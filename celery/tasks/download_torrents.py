from time import sleep
from config.celeryconfig import app
from celery.signals import worker_process_init
from celery_singleton import Singleton

@worker_process_init.connect
def initialize_torrent_session(**kwargs):
    global torrent_downloader
    from config.torrent_downloader import TorrentDownloader
    torrent_downloader = TorrentDownloader.get_instance()

@app.task(name='download_torrents')
def download_torrents(magnet_link, movie_key):
    global torrent_downloader
    # if not torrent_downloader: return {}
    info = torrent_downloader.add_torrent(magnet_link, movie_key)
    return info

# @app.on_after_configure.connect
# def setup_periodic_tasks(sender, **_):
#     sender.add_periodic_task(60.0, process_jobs.s(), name='process_jobs')

@app.task(
    name='process_jobs',
    base=Singleton,
    # lock_expiry=60, 
    # raise_on_duplicate=False
)
def process_jobs():
    print("Processing jobs")
    global torrent_downloader
    while True:
        print("_______________________________________")
        print("dora")
        active_jobs = False
        for job in torrent_downloader.jobs:
            print(f"Processing job: {job}")
            active_jobs = True
            # Process your job here

        if not active_jobs:
            print("No active jobs, task completing")
            break

        self.time.sleep(10)

    return {}

# @app.task(name='get_torrent_info')
# def get_torrent_info(movie_key):
#     global torrent_downloader
#     if not torrent_downloader: return {}
#     info = torrent_downloader.get_torrent_info(movie_key)
#     return info
