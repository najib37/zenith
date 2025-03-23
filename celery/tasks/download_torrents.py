import mimetypes
from time import sleep

# from celery.utils import time
import libtorrent as lt
from celery.signals import worker_process_init, worker_shutdown
from celery_singleton import Singleton
from tasks.converter import ConverterStatus, VideoConverter, VideoResulotion

from celery import Celery

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

        self.jobs = {}

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

    def get_metadata(self, handle):
        time = 0
        while not handle.status().has_metadata:
            if time > 10:
                raise TorrentTimeoutError("Torrent metadata download timeout")
            # TODO: add cleanup and use celery sleep
            sleep(0.5)
            time += 0.5

    def set_mime_types(self):
        mimetypes.init()
        mimetypes.add_type("video/x-matroska", ".mkv")
        mimetypes.add_type("video/mp4", ".mp4")


    def add_torrent(self, magnet_link, movie_key):
        if movie_key in self.jobs:
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
                # "path": "/home/data/hls/na.mkv",
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

        process_jobs.delay()

        formated_metadata = {
            "status": "torrent_added_success",
            "code": 200,
            "files": files,
            "info": self.get_info_from_handle(handle),
        }

        print(f"Added torrent: {movie_key}")
        return formated_metadata

    def post_process(self, movie_key, movie_info):
        match str(movie_info["type"]):
            case "video/x-matroska":
                converter = VideoConverter(
                    movie_info["path"], "/home/data/movies/outs", movie_key
                )
                return converter
            case "video/mp4":
                pass
            case _:
                pass

    def get_jobs(self):
        return self.jobs


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
    if torrent_downloader:
        torrent_downloader.session.pause()
        for _, job in torrent_downloader.jobs.items():
            handler, converter = job.values()
            converter.stop_conversion()
            handler.pause()

@app.task(
    name="download_torrents",
    queue="torrent_queue",
)
def download_torrents(magnet_link, movie_key):
    # global torrent_donloader

    torrent_downloader = TorrentDownloader.get_instance()

    try:
        info = torrent_downloader.add_torrent(magnet_link, movie_key)
        return info
    except TorrentTimeoutError as e:
        raise  # This will propagate directly to the client

    torrent_downloader = TorrentDownloader.get_instance()

    print("+-" * 100) 
    print("+-" * 100)
    for key, job in torrent_downloader.jobs.items():
        print(f"key: {key} - job: {job}")
    print("+-" * 100)
    print("+-" * 100)

    info = torrent_downloader.add_torrent(magnet_link, movie_key)
    return info


@app.task(
    name="process_jobs",
    base=Singleton,
    queue="torrent_queue",
    # lock_expiry=60,
    # raise_on_duplicate=False
)
def process_jobs():
    a = 0
    torrent_downloader = TorrentDownloader.get_instance()

    while len(torrent_downloader.jobs) > 0:
        print("dora ---------------------------------")

        return {}

        for key, job in torrent_downloader.jobs.items():
            handler, converter = job.values()

            if not handler.status().paused and handler.status().progress >= 0.1:
                print("=" * 100)
                print("=" * 100)
                print("Pause download")
                print("=" * 100)
                print("=" * 100)
                handler.pause()

            # full downloaded and converted job completed
            if handler.status().is_finished and converter.status == ConverterStatus.DONE:
                print("_" * 100)
                print("_" * 100)
                print("downloaded and converted")
                print("_" * 100)
                print("_" * 100)
                converter.stop_conversion()
                del torrent_downloader.jobs[key]
                continue

            # init conversion
            if handler.status().downloading and converter.status == ConverterStatus.IDLE:
                print("_" * 100)
                print("_" * 100)
                print("Start conversion")
                print("_" * 100)
                print("_" * 100)
                converter.start_conversion()
            #
            # # full downloaded but not converted
            # if handler.status().is_finished and converter.status != ConverterStatus.CONVERTING:
            #     continue
            #
            # # download paused pause conversion 
            # if handler.status().paused and converter.status == ConverterStatus.CONVERTING:
            #     converter.pause_conversion()

            print(f"Downloading: {handler.status().progress * 100}% - Download Rate: {handler.status().download_rate / 1024} KB/s")

            sleep(1)

        # a += 1
        # if a > 10:
        #     break

    return {
        "status": "done",
        "code": 200,
    }


# @app.task(name='get_torrent_info')
# def get_torrent_info(movie_key):
#     global torrent_downloader
#     if not torrent_downloader: return {}
#     info = torrent_downloader.get_torrent_info(movie_key)
#     return info
