from time import sleep
import libtorrent as lt
import subprocess
import os

def download_and_convert(magnet_link, output_file):
    # Configure torrent session for sequential download

    session = lt.session()
    params = lt.parse_magnet_uri(magnet_link)
    params.save_path = '/home/data/temp/'
    params.storage_mode = lt.storage_mode_t.storage_mode_sparse
    
    handle = session.add_torrent(params)
    # handle.set_sequential_download(True)
    
    while not handle.has_metadata():
        sleep(1)
    piece_size = handle.torrent_file().piece_length()
    total_pieces = handle.torrent_file().num_pieces()

        
    
    # Set up FFmpeg process
    ffmpeg = subprocess.Popen([
        'ffmpeg',
        '-i', 'pipe:0',  # Read from stdin
        '-c:v', 'h264',  # Use your desired codec
        '-c:a', 'aac',
        output_file
    ], stdin=subprocess.PIPE)
    
    # Buffer for incomplete pieces
    buffer = b''
    last_piece = 0
    
    while handle.status().state != lt.torrent_status.seeding:
        # Get piece availability
        have_pieces = handle.have_pieces()
        
        # Process new complete pieces
        for i in range(last_piece, total_pieces):
            if have_pieces[i]:
                piece_data = handle.read_piece(i)
                ffmpeg.stdin.write(piece_data)
                last_piece = i + 1
            else:
                break
                
        session.wait_for_alert(1000)
    
    ffmpeg.stdin.close()
    ffmpeg.wait()
    sess.remove_torrent(handle)

# Usage
magnet_link = "magnet:?xt=urn:btih:C7C6FC39B7CCA0CAE1F65F166179F10C4FDC7347&dn=The+Gutter+2024+1080p+WEB-DL+HEVC+x265+5.1+BONE&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fopentracker.io%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.dler.org%3A6969%2Fannounce&tr=udp%3A%2F%2Fr.l5.ca%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.dler.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2F&tr=http%3A%2F%2Ftracker.bt4g.com%3A2095%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce&tr=https%3A%2F%2Ftracker.gcrenwp.top%3A443%2Fannounce&tr=udp%3A%2F%2Ftracker.0x7c0.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fttk2.nbaonlineservice.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fbandito.byterunner.io%3A6969%2Fannounce&tr=udp%3A%2F%2Fevan.im%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=http%3A%2F%2Ftracker.openbittorrent.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopentracker.i2p.rocks%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Fcoppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.zer0day.to%3A1337%2Fannounce"

output_file = "converted_output.mp4"
download_and_convert(magnet_link, output_file)

