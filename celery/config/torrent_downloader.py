import libtorrent as lt
from time import sleep
import mimetypes
from tasks.converter import VideoConverter
from tasks.download_torrents import process_jobs

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
        self.session.add_extension('ut_metadata')
        self.session.add_extension('ut_pex')

        self.jobs = {}

    def get_info_from_handle(self, handle):
        info = {
            "name": handle.status().name,
            "progress": handle.status().progress * 100,  # Convert to percentage
            "download_rate": handle.status().download_rate / 1024,  # Convert to KB/s
            "upload_rate": handle.status().upload_rate / 1024,  # Convert to KB/s
            "num_peers": handle.status().num_peers,
            "num_seeds": handle.status().num_seeds,
            "total_size": handle.status().total_wanted / (1024 * 1024),  # Convert to MB
            "total_downloaded": handle.status().total_done / (1024 * 1024),  # Convert to MB
            "state": str(handle.status().state),
            "paused": handle.status().paused,
            "is_finished": handle.status().is_finished,
            "is_seed": handle.status().is_seeding,
        }
        return info

    def add_torrent(self, magnet_link, movie_key):

        # process_jobs.delay()
        return {}
        # if movie_key in self.jobs:
        #     return {
        #         "status": "torrent_already_added",
        #         "code": 200,
        #         "info": self.get_info_from_handle(self.jobs[movie_key]['handle']),
        #     }
        #
        # relative_path = f"/movies/{str(movie_key)}/"
        # full_path = f"/home/data/movies/{str(movie_key)}/"
        # params = lt.parse_magnet_uri(magnet_link)
        # params.save_path = full_path
        # params.storage_mode = lt.storage_mode_t.storage_mode_allocate
        # handle = self.session.add_torrent(params)
        # handle.set_sequential_download(True)
        # mimetypes.init()
        # mimetypes.add_type('video/x-matroska', '.mkv')
        # mimetypes.add_type('video/mp4', '.mp4')
        #
        # time = 0
        # while not handle.status().has_metadata:
        #     if time > 10: return {
        #         "status": "no_metadata",
        #         "code": 404
        #     }
        #     # TODO: add cleanup and use celery sleep
        #     sleep(0.5)
        #     time += 0.5
        #
        # files = [
        #     {
        #         "path": f"{full_path}/{f.path}",
        #         "size": f.size,
        #         "type": mimetypes.guess_type(f.path)[0]
        #     }
        #     for f in handle.status().torrent_file.files()
        # ]
        #
        # largest_file = max(files, key=lambda x: x['size'])
        #
        #
        # converter = self.post_process(movie_key, largest_file)
        #
        # self.jobs[movie_key] = {
        #     "handle": handle,
        #     "converter": converter
        # }
        #
        #
        # formated_metadata = {
        #     "status": "torrent_added_success",
        #     "code": 200,
        #     "files": files,
        #     "duration": converter.get_video_duration(largest_file['path']) if converter else 0,
        #     "info": self.get_info_from_handle(handle),
        # }
        #
        # print(f"Added torrent: {movie_key}")
        # process_jobs.delay()
        #
        # return formated_metadata

    def post_process(self, movie_key, movie_path):
        match str(movie_path['type']):
            case 'video/x-matroska':
                converter = VideoConverter(movie_path['path'], movie_path['path'], movie_key)
                return converter
            case 'video/mp4':
                pass
            case _:
                pass

