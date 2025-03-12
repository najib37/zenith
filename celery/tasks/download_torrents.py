
from time import sleep
from config.celeryconfig import TorrentDownloader, app


# @app.task(name='download_torrents')
# def download_torrents(magnet_link, movie_key):
#     downloader = TorrentDownloader()
#     info = downloader.add_torrent(magnet_link, movie_key)
#
#     print("________________________________________")
#     print(f"got info {info}")
#     print("________________________________________")
#     return info

# @app.task(name='get_torrent_info')
# def get_torrent_info(movie_key):
#     info = downloader.get_torrent_info(movie_key)
#     return info
#

from config.celeryconfig import TorrentDownloader, app
from celery.signals import worker_process_init
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
torrent_downloader = None

@worker_process_init.connect
def initialize_torrent_session(**kwargs):
    global torrent_downloader
    torrent_downloader = TorrentDownloader.get_instance()
    logger.info("LibTorrent session initialized")

@app.task(name='download_torrents')
def download_torrents(magnet_link, movie_key):
    global torrent_downloader
    if not torrent_downloader: return {}
    info = torrent_downloader.add_torrent(magnet_link, movie_key)
    logger.info(f"Added torrent: {info}")
    return info

@app.task(name='get_torrent_info')
def get_torrent_info(movie_key):
    global torrent_downloader
    if not torrent_downloader: return {}
    info = torrent_downloader.get_torrent_info(movie_key)
    return info
