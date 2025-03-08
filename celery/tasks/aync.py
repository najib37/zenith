import libtorrent as lt
import asyncio
import sys
from time import sleep

async def get_torrent_metadata(magnet_link):
    session = lt.session()
    
    # Add extensions
    session.add_extension('ut_metadata')
    session.add_extension('ut_pex')
    
    # Add magnet
    params = {
        'save_path': './temp',  # Temporary save path
        'storage_mode': lt.storage_mode_t.storage_mode_sparse,
    }
    
    handle = lt.add_magnet_uri(session, magnet_link, params)
    
    print("Fetching metadata...")
    
    # Wait for metadata
    while not handle.has_metadata():
        await asyncio.sleep(1)
    
    # Get the torrent info
    torrent_info = handle.get_torrent_info()
    
    # Print basic metadata
    print("\nTorrent Metadata:")
    print(f"Name: {torrent_info.name()}")
    print(f"Number of files: {torrent_info.num_files()}")
    print(f"Total size: {torrent_info.total_size() / 1024 / 1024:.2f} MB")
    
    # Print file details
    print("\nFiles:")
    for f in torrent_info.files():
        print(f"- {f.path}: {f.size / 1024 / 1024:.2f} MB")
    
    # Cleanup
    session.remove_torrent(handle)
    
async def main():
    # if len(sys.argv) != 2:
    #     print("Usage: python script.py <magnet_link>")
    #     sys.exit(1)
        
    # magnet_link = sys.argv[1]
    await get_torrent_metadata("""magnet:?xt=urn:btih:4C9B41D664D7B6B23F0BF39AE185858CBADDA3FF&dn=SpiderMan+No+Way+Home+2021+1080p+HD-TS+V3+Line+Audio+x264+AAC&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fexodus.desync.com%3A6969%2Fannounce&tr=udp%3A%2F%2F9.rarbg.me%3A2970%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.tiny-vps.com%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Fopentor.org%3A2710%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce&tr=udp%3A%2F%2Fexplodie.org%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.moeking.me%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.cyberia.is%3A6969%2Fannounce&tr=udp%3A%2F%2F9.rarbg.me%3A2980%2Fannounce&tr=udp%3A%2F%2F9.rarbg.to%3A2940%2Fannounce&tr=udp%3A%2F%2Ftracker.uw0.xyz%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=http%3A%2F%2Ftracker.openbittorrent.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopentracker.i2p.rocks%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Fcoppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.zer0day.to%3A1337%2Fannounce""")

if __name__ == "__main__":
    asyncio.run(main())


