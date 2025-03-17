from config.celeryconfig import TorrentDownloader, app
from celery.signals import worker_process_init

torrent_downloader = None

@worker_process_init.connect
def initialize_torrent_session(**kwargs):
    global torrent_downloader
    torrent_downloader = TorrentDownloader.get_instance()

@app.task(name='download_torrents')
def download_torrents(magnet_link, movie_key):
    print("++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++")
    print("downloading torrent")
    print("++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++")
    global torrent_downloader
    if not torrent_downloader: return {}
    print("++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++")
    print("donwser exists")
    print("++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++")
    info = torrent_downloader.add_torrent(magnet_link, movie_key)
    return info

# @app.task(name='get_torrent_info')
# def get_torrent_info(movie_key):
#     global torrent_downloader
#     if not torrent_downloader: return {}
#     info = torrent_downloader.get_torrent_info(movie_key)
#     return info
