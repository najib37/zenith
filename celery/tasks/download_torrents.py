import mimetypes
import os
from time import sleep
from celery.exceptions import Ignore

import libtorrent as lt
import py1337x
from celery import Celery, group
from celery.signals import worker_process_init, worker_shutdown
from py1337x.types import category, order
import requests
from tasks.conr import Converter
from tasks.subtitles_downloader import SubtitlesDownloader


class TorrentTimeoutError(Exception):
    pass


app = Celery(
    "tasks",
    broker="amqp://userf:userd@rabbitmq:5672",
    backend="redis://redis:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    # singleton_backend_url='redis://redis:6379/0',
    enable_utc=True,
)


class TorrentDownloader:

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if TorrentDownloader._instance is not None:
            raise Exception("This class is a singleton! Use get_instance() instead")
        self.session = lt.session()
        self.session.add_extension("ut_metadata")
        self.session.add_extension("ut_pex")
        self.searcher = py1337x.Py1337x()
        settings = {
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "max_retry_port_bind": 10,
            "peer_connect_timeout": 3,
            "request_timeout": 5,
            "allow_multiple_connections_per_ip": True,
            "send_buffer_watermark": 1048576,  # 1MB
            "active_seeds": -1,  # Unlimited active seeds
            "dht_bootstrap_nodes": "router.bittorrent.com:6881,router.utorrent.com:6881,dht.transmissionbt.com:6881",
            "max_peerlist_size": 10000,  # Increase max peers list
            "dht_upload_rate_limit": 100000,  # 100kB/s for DHT
            "active_downloads": -1,  # Unlimited active downloads
        }
        self.session.apply_settings(settings)

        self.jobs = {}

    def get_metadata(self, handle, timeout=10):
        time = 0
        while not handle.status().has_metadata:
            if time > timeout:
                raise TorrentTimeoutError("Torrent metadata download timeout")
            # TODO: add cleanup and use celery sleep
            sleep(1)
            time += 1

    def get_metadata_sync(self, magnet_link, movie_key, timeout=10):
        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = "/home/data/movies/"
        params.storage_mode = lt.storage_mode_t.storage_mode_allocate
        params.flags |= lt.torrent_flags.update_subscribe  # Add this line
        handle = self.session.add_torrent(params)
        self.set_mime_types()

        try:
            time = 0
            while not handle.status().has_metadata:
                if time >= timeout:
                    self.delete_torrent_download(handle)
                    raise TorrentTimeoutError("Torrent metadata download timeout")
                sleep(1)
                time = time + 1

            status = handle.status()
            self.delete_torrent_download(handle)
            biggest_file = max(status.torrent_file.files(), key=lambda x: x.size)
            return {
                "status": "success",
                "magnet_link": magnet_link,
                "movie_key": movie_key,
                "result": {
                    "name": status.name,
                    "progress": status.progress * 100,  # Convert to percentage
                    "download_rate": status.download_rate / 1024,  # Convert to KB/s
                    "upload_rate": status.upload_rate / 1024,  # Convert to KB/s
                    "num_peers": status.num_peers,
                    "num_seeds": status.num_seeds,
                    "total_size": status.total_wanted / (1024 * 1024),  # Convert to MB
                    "total_downloaded": status.total_done
                    / (1024 * 1024),  # Convert to MB
                    "state": str(status.state),
                    "paused": status.paused,
                    "is_finished": status.is_finished,
                    "is_seed": status.is_seeding,
                    "file": {
                        "name": biggest_file.path,
                        "path": f"/home/data/movies/{biggest_file.path}",
                        "size": biggest_file.size,
                        "type": mimetypes.guess_type(biggest_file.path)[0],
                    },
                },
            }
        except Exception as e:
            return {}

    def get_info_from_handle(self, handle):
        self.get_metadata(handle)
        info = {
            "name": handle.status().name,
            "progress": handle.status().progress * 100,  # Convert to percentage
            "download_rate": handle.status().download_rate / 1024,  # Convert to KB/s
            "upload_rate": handle.status().upload_rate / 1024,  # Convert to KB/s
            "num_peers": handle.status().num_peers,
            "num_seeds": handle.status().num_seeds,
            "total_size": handle.status().total_wanted / (1024 * 1024),  # Convert to MB
            "total_downloaded": handle.status().total_done
            / (1024 * 1024),  # Convert to MB
            "state": str(handle.status().state),
            "paused": handle.status().paused,
            "is_finished": handle.status().is_finished,
            "is_seed": handle.status().is_seeding,
        }
        return info

    def set_mime_types(self):
        mimetypes.init()
        mimetypes.add_type("video/x-matroska", ".mkv")
        mimetypes.add_type("video/mp4", ".mp4")

    def add_torrent(self, magnet_link, movie_key):
        if movie_key in self.jobs:
            conversion_task.delay(movie_key)
            return {
                "status": "torrent_already_added",
                "code": 200,
                "info": self.get_info_from_handle(self.jobs[movie_key]["handle"]),
            }

        relative_path = f"/movies/{str(movie_key)}/"
        full_path = f"/home/data/movies/{str(movie_key)}/"
        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = full_path
        params.storage_mode = lt.storage_mode_t.storage_mode_allocate
        handle = self.session.add_torrent(params)
        handle.set_flags(lt.torrent_flags.sequential_download)
        self.set_mime_types()
        self.get_metadata(handle)

        files = [
            {
                "path": f"{full_path}/{f.path}",
                "size": f.size,
                "type": mimetypes.guess_type(f.path)[0],
            }
            for f in handle.status().torrent_file.files()
        ]

        movie_info = max(files, key=lambda x: x["size"])

        converter = self.post_process(movie_key, movie_info)

        self.jobs[movie_key] = {
            "handle": handle,
            "converter": converter,
        }

        formated_metadata = {
            "status": "torrent_added_success",
            "code": 200,
            "files": files,
            "info": self.get_info_from_handle(handle),
        }

        conversion_task.delay(movie_key)

        print(f"Added torrent: {movie_key}")

        return formated_metadata

    def delete_torrent_download(self, handle, delete_files=True):
        handle.pause()
        self.session.remove_torrent(handle, 1 if delete_files else 0)

    def post_process(self, movie_key, movie_info):
        print("." * 20)
        print("." * 20)
        print(f"Post process {movie_key}")
        # print(f"Post process {movie_info["type"]}")
        print("." * 20)
        print("." * 20)

        match str(movie_info["type"]):
            case "video/x-matroska":
                converter = Converter(
                    movie_info["path"], f"/home/data/movies/outs/{movie_key}"
                )
                return converter
            case "video/mp4":
                pass
            case _:
                pass


@worker_process_init.connect
def initialize_torrent_session(**kwargs):
    global torrent_downloader

    print("Initializing torrent session")
    torrent_downloader = TorrentDownloader.get_instance()


@worker_shutdown.connect
def cleanup_on_shutdown(**kwargs):
    """Perform cleanup when worker shuts down"""
    # global torrent_downloader

    torrent_downloader = TorrentDownloader.get_instance()
    if not torrent_downloader:
        return

    torrent_downloader.session.pause()
    for _, job in torrent_downloader.jobs.items():
        handler, converter = job.values()
        converter.stop_conversion()
        handler.pause()

# @app.task(
#     name="get_torrent_info",
#     queue="torrent_queue"
# )
# def get_torrent_info_task(magnet_link):
#     torrent_downloader = TorrentDownloader.get_instance()
#
#     print(f"get_torrent_info_task {magnet_link}")
#     try:
#         # handle = torrent_downloader.temp_add_torrent(magnet_link)
#         result = torrent_downloader.get_metadata_sync(magnet_link)
#         return handle.status().name if result else None
#     except TorrentTimeoutError as e:
#         raise

# @app.task(
#     name="get_metadata",
#     queue="torrent_queue",
# )
# def get_metadata_task(links):
#     try:
#         task_group = group(get_torrent_info_task.s(link) for link in links)
#         result = task_group.apply_async()
#         return result.get()
#     except TorrentTimeoutError as e:
#         raise


@app.task(name="get_movie_info", queue="torrent_queue")
def get_movie_info_task(torrent_id):
    torrent_downloader = TorrentDownloader.get_instance()
    try:
        torrents = torrent_downloader.searcher
        result = torrents.info(torrent_id=torrent_id)
        result = torrent_downloader.get_metadata_sync(result.magnet_link, torrent_id)

        return result

    except TorrentTimeoutError as e:
        raise


@app.task(name="search_movies", queue="torrent_queue")
def search_movies_task(movie_name):
    torrent_downloader = TorrentDownloader.get_instance()
    try:
        torrents = torrent_downloader.searcher
        results = torrents.search(
            f"{movie_name}", sort_by=py1337x.sort.SEEDERS, category=category.MOVIES
        )
        torrent_ids = [res.torrent_id for res in results.items[:10]]

        search_task = group(
            get_movie_info_task.s(torrent_id) for torrent_id in torrent_ids
        )
        result = search_task.apply_async()
        task_result = result.get(disable_sync_subtasks=False)

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
#
# @app.task(
#     name="download_torrents",
#     queue="torrent_queue",
# )
# def download_torrents(magnet_link, movie_key):
#     torrent_downloader = TorrentDownloader.get_instance()
#     try:
#         info = torrent_downloader.add_torrent(magnet_link, movie_key)
#         return info
#     except TorrentTimeoutError as e:
#         raise  # This will propagate directly to the client

@app.task(
    name="download_movie_task",
    queue="torrent_queue",
)
def download_movie_task(movie_name):
    torrent_downloader = TorrentDownloader.get_instance()

    def wait_file_creation(file_path, timeout=20):
        while not os.path.exists(file_path):
            # if timeout <= 0:
            #     raise TorrentTimeoutError("File creation timeout")
            print(f"Waiting for file creation: {file_path}")
            timeout -= 1
            sleep(1)
    try:
        search_task = search_movies_task.delay(movie_name)
        result = search_task.get(disable_sync_subtasks=False)

        if result.get("code") == 404:
            return {
                "status": "no_results",
                "code": 404,
            }

        movie_key = result.get("movie_key")
        magnet_link = result["magnet_link"]
        file_name = result["result"]["file"]["name"]
        sub_task = download_subtitles_task.delay(file_name).get(disable_sync_subtasks=False)
        print("+" * 20)
        print("+" * 20)
        print(f"Downloading movie {file_name}")
        print("+" * 20)
        print("+" * 20)
        # torrent_downloader.add_torrent(magnet_link, movie_key)
        # converter = torrent_downloader.jobs[movie_key]["converter"]
        # wait_file_creation(f"{converter.output_path}/144/144p.m3u8", timeout=20)

        return {
            "status": "done",
            "subs": sub_task,
            "code": 200,
        }
    except TorrentTimeoutError as e:
        raise

@app.task(
    name="convert_video",
    queue="torrent_queue",
    ignore_result=True,
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
def download_subtitles_task(movie_name):
    sub = SubtitlesDownloader.get_sub_id(movie_name)

    return sub or {}

