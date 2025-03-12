
from celery import Celery
import json
import libtorrent as lt
from time import sleep

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

        params = lt.parse_magnet_uri(magnet_link)
        params.save_path = f'/home/data/movies/{movie_key}/'
        params.storage_mode = lt.storage_mode_t.storage_mode_sparse

        handle = self.session.add_torrent(params)

        # self.handles[movie_key] = handle

        return {"status": "torrent_added_success"}

    def get_torrent_status(self, movie_key):
        handle = self.handles.get(movie_key)

        if not handle:
            return None
        return handle.status()

    def remove_torrent(self, movie_key):
        handle = self.handles.get(movie_key)
        self.session.remove_torrent(handle)
