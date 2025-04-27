import mimetypes
import os
from time import sleep

import libtorrent as lt
from tasks.video_converter import Converter


class TorrentTimeoutError(Exception):
    pass

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
            if movie_key not in self.jobs:
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
            return {
                "status": "torrent_already_added",
                "code": 200,
                "data": self.get_info_from_handle(self.jobs[movie_key]["handle"]),
            }

        try:
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
                "data": self.get_info_from_handle(handle),
            }
            return formated_metadata

        except Exception as e:
            print(f"Error adding torrent: {e}")
            return {
                "status": "torrent_add_error",
                "code": 500,
                "error": str(e),
            }

    def delete_torrent_download(self, handle, delete_files=True):
        handle.pause()
        self.session.remove_torrent(handle, 1 if delete_files else 0)

    def post_process(self, movie_key, movie_info):

        match str(movie_info["type"]):
            case "video/x-matroska":
                converter = Converter(
                    movie_info["path"], f"/home/data/movies/outs/{movie_key}"
                )
                return converter
            case "video/mp4":
                # not implemented yet
                pass
            case _:
                pass
