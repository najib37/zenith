import os
from time import sleep

import py1337x
from celery.signals import worker_process_init, worker_shutdown
from py1337x.types import category
from tasks.download_torrents import TorrentDownloader, TorrentTimeoutError
from tasks.subtitles_downloader import SubtitlesDownloader

from celery import Celery, group

app = Celery(
    "tasks",
    broker="amqp://userf:userd@rabbitmq:5672",
    backend="redis://redis:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

client_1337 = py1337x.Py1337x()


@worker_process_init.connect
def initialize_torrent_session(**kwargs):
    global torrent_downloader

    print("Initializing torrent session")
    torrent_downloader = TorrentDownloader.get_instance()


@worker_shutdown.connect
def cleanup_on_shutdown(**kwargs):
    torrent_downloader = TorrentDownloader.get_instance()
    if not torrent_downloader or not torrent_downloader.session:
        return

    torrent_downloader.session.pause()
    for _, job in torrent_downloader.jobs.items():
        handler, converter = job.values()
        converter.stop_conversion()
        handler.pause()


@app.task(name="get_movie_info", queue="torrent_queue")
def get_movie_info_task(torrent_id):
    torrent_downloader = TorrentDownloader.get_instance()
    try:
        result = client_1337.info(torrent_id=torrent_id)
        result = torrent_downloader.get_metadata_sync(result.magnet_link, torrent_id)

        return result

    except TorrentTimeoutError as e:
        raise


@app.task(name="search_movies", queue="torrent_queue")
def search_movies_task(movie_name):
    try:
        results = client_1337.search(
            f"{movie_name}", sort_by=py1337x.sort.SEEDERS, category=category.MOVIES
        )
        torrent_ids = [res.torrent_id for res in results.items[:10]]

        search_task = group(
            get_movie_info_task.s(torrent_id) for torrent_id in torrent_ids
        )
        task_result = search_task.apply_async().get(disable_sync_subtasks=False)

        if not task_result:
            return {
                "status": "no_results",
                "code": 404,
            }

        info = sorted(
            [
                res
                for res in task_result
                if res
                and (
                    res.get("result", {}).get("file", {}).get("type")
                    == "video/x-matroska"
                )
            ],
            key=lambda x: x["result"]["num_seeds"],
            reverse=True,
        )

        if not info or len(info) == 0:
            return {
                "status": "no_results",
                "code": 404,
            }
        return info[0]

    except TorrentTimeoutError as e:
        raise


@app.task(
    name="download_movie_task",
    queue="torrent_queue",
)
def download_movie_task(movie_name):
    torrent_downloader = TorrentDownloader.get_instance()
    torrent_info = {}

    try:
        search_task = search_movies_task.delay(movie_name)
        result = search_task.get(disable_sync_subtasks=False)
        if result.get("code", 0) == 404:
            return {
                "status": "no_results",
                "code": 404,
            }

        movie_key = result.get("movie_key", "")
        magnet_link = result.get("magnet_link", "")
        file_name = result.get("result", {}).get("file", {}).get("name", "")

        subtitles_task = download_subtitles_task.delay(file_name, movie_key)

        if movie_key not in torrent_downloader.jobs:
            torrent_info = torrent_downloader.add_torrent(magnet_link, movie_key)
        else:
            torrent_info = torrent_downloader.get_info_from_handle(
                torrent_downloader.jobs[movie_key]["handle"]
            )

        conversion_task.delay(movie_key)
        subs_result = subtitles_task.get(disable_sync_subtasks=False)
        converter = torrent_downloader.jobs[movie_key]["converter"]

        try:
            wait_file_creation(f"{converter.output_path}/144/144p.m3u8", timeout=60)
        except TorrentTimeoutError as e:
            print(f"Error waiting for file creation: {e}")
            converter.stop_conversion()
            torrent_downloader.delete_torrent_download(
                torrent_downloader.jobs[movie_key]["handle"]
            )
            torrent_downloader.jobs.pop(movie_key, None)
            return {
                "status": "file_creation_timeout",
                "code": 500,
            }

        return {
            "code": 200,
            "status": "started",
            "static_path": converter.output_path,
            "subtitles_result": subs_result,
            "torrent_result": torrent_info,
        }
    except Exception as e:
        raise


@app.task(
    name="convert_video",
    queue="torrent_queue",
    # ignore_result=True,
)
def conversion_task(movie_key):
    torrent_downloader = TorrentDownloader.get_instance()

    # return {}

    if movie_key not in torrent_downloader.jobs:
        return {
            "status": "movie_key_not_found",
            "code": 404,
        }

    handler, converter = torrent_downloader.jobs[movie_key].values()

    converter.start_conversion(handler)

    return {
        "status": "done",
        "code": 200,
    }

@app.task(
    name="download_subtitles_task",
    queue="torrent_queue",
)
def download_subtitles_task(movie_name, movie_key):
    sub = SubtitlesDownloader.get_sub_id(movie_name)
    if len(sub) != 0:
        SubtitlesDownloader.download_sub(sub, f"/home/data/movies/outs/{movie_key}/subs/")

    return sub or {}

def wait_file_creation(file_path, timeout=20):

    while not os.path.exists(file_path) and timeout > 0:
        print(f"Waiting for file creation: {file_path}")
        timeout -= 1
        sleep(1)
    if timeout <= 0:
        raise TorrentTimeoutError(f"File creation timed out: {file_path}")
