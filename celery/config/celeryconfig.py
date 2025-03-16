
import asyncio
from celery import Celery
import json
import libtorrent as lt
from time import sleep
import mimetypes

from tasks.converter import VideoConverter

app = Celery('tasks')

app.conf.update(
    broker_url='amqp://userf:userd@rabbitmq:5672',
    result_backend='rpc://',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
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
    # def __init__(self):
        self.session = lt.session()

        self.session.add_extension('ut_metadata')
        self.session.add_extension('ut_pex')
        self.torrents = []
        self.handles = {}
    
    def get_torrent_metadata(self, magnet_link):
        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = '/home/data/temp/'
        params.storage_mode = lt.storage_mode_t.storage_mode_sparse
        
        handle = self.session.add_torrent(params)
        
        while not handle.has_metadata():
            sleep(1)
        
        torrent_info = handle.get_torrent_info()

        formated_metadata = {
            "name": torrent_info.name(),
            "num_files": torrent_info.num_files(),
            "total_size": torrent_info.total_size() / 1024 / 1024,
            "files": torrent_info.files()
        }
        self.session.remove_torrent(handle)
        return formated_metadata

    def get_torrent_info(self, movie_key):
        handle = self.handles.get(movie_key)
        if not handle:
            return {
                "status": "no data found",
            }
        
        status = handle.status()

        info = {
            "name": status.name,
            "progress": status.progress * 100,  # Convert to percentage
            "download_rate": status.download_rate / 1024,  # Convert to KB/s
            "upload_rate": status.upload_rate / 1024,  # Convert to KB/s
            "num_peers": status.num_peers,
            "num_seeds": status.num_seeds,
            "total_size": status.total_wanted / (1024 * 1024),  # Convert to MB
            "total_downloaded": status.total_done / (1024 * 1024),  # Convert to MB
            "state": str(status.state),
            "paused": status.paused,
            "is_finished": status.is_finished,
            "is_seed": status.is_seeding,
            "total_files": status.torrent_file,
        }
        return json.dumps(info)

    def add_torrent(self, magnet_link, movie_key):
        relative_path = f"/movies/{str(movie_key)}/"
        full_path = f"/home/data/movies/{str(movie_key)}/"
        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = full_path
        params.storage_mode = lt.storage_mode_t.storage_mode_allocate
        handle = self.session.add_torrent(params)
        handle.set_sequential_download(True)
        mimetypes.init()
        mimetypes.add_type('video/x-matroska', '.mkv')
        mimetypes.add_type('video/mp4', '.mp4')

        time = 0
        while not handle.status().has_metadata:
            if time > 10: return {
                "status": "no_metadata",
                "code": 404
            }
            # TODO: add cleanup
            sleep(0.5)
            time += 0.5

        self.handles[movie_key] = handle

        files = [
            {
                "path": f"{relative_path}/{f.path}",
                "size": f.size,
                "type": mimetypes.guess_type(f.path)[0]
            }
            for f in handle.status().torrent_file.files()
        ]
        
        largest_file = max(files, key=lambda x: x['size'])

        formated_metadata = {
            "status": "torrent_added_success",
            "code": 200,
            "files": files
        }

        post = PostProcess(movie_key, largest_file)
        post.post_process(movie_key, largest_file)

        return formated_metadata

    def get_torrent_status(self, movie_key):
        handle = self.handles.get(movie_key)

        if not handle:
            return None
        return handle.status()

    def remove_torrent(self, movie_key):
        handle = self.handles.get(movie_key)
        self.session.remove_torrent(handle)

class PostProcess:
    def __init__(self, movie_key, movie_path):
        self.torrent_downloader = TorrentDownloader.get_instance()
        self.converter = VideoConverter(input_file=movie_path)
    
    def post_process(self, movie_key, movie_path):

        match str(movie_path['type']):
            case 'video/x-matroska':
                self.processMkv(movie_key, movie_path)
            case 'video/mp4':
                pass
            case _:
                pass

    def processMkv(self, movie_key, movie_path):
        print("Processing MKV")
        self.converter.start_conversion()

    def processMp4(self, movie_key, movie_path):
        pass

    def processOther(self, movie_key, movie_path):
        pass
