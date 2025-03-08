
from config.celeryconfig import downloader, app

@app.task(name='download_torrents')
def download_torrents(magnet_link, movie_key):
    downloader.get_torrent_metadata(magnet_link)
    downloader.add_torrent(magnet_link, movie_key)
    info = downloader.get_torrent_info(movie_key)
    return info

@app.task(name='get_torrent_info')
def get_torrent_info(movie_key):
    info = downloader.get_torrent_info(movie_key)
    return info
