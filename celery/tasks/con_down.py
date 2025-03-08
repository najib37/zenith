from time import sleep
import libtorrent as lt
import subprocess
import os
from io import BytesIO

class StreamingStorage(lt.file_storage):
    def __init__(self, save_path):
        super().__init__()
        self.save_path = save_path
        self.buffers = {}
        self.ffmpeg_processes = {}

    def initialize_file(self, index, handle):
        file_info = handle.get_torrent_info().files()
        file_path = file_info.file_path(index)
        if file_path.endswith(('.mp4', '.mkv', '.avi')):
            output_path = os.path.join(self.save_path, f"{os.path.splitext(file_path)[0]}.mp4")
            
            # Setup ffmpeg process
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', 'pipe:0',  # Read from stdin
                '-c:v', 'libx264',  # Video codec
                '-c:a', 'aac',      # Audio codec
                '-movflags', '+faststart',
                output_path
            ]
            
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.ffmpeg_processes[index] = process
            self.buffers[index] = BytesIO()

    def write_piece(self, piece, piece_index, offset, size):
        handle = self.current_handle
        piece_size = handle.get_torrent_info().piece_size(piece_index)
        file_info = handle.get_torrent_info().files()
        
        # Map piece to file(s)
        files = self.map_piece_to_files(piece_index, piece_size, file_info)
        
        for file_index, (file_offset, file_size) in files.items():
            if file_index in self.ffmpeg_processes:
                # Write to ffmpeg process
                data = piece[file_offset:file_offset + file_size]
                self.ffmpeg_processes[file_index].stdin.write(data)
                self.ffmpeg_processes[file_index].stdin.flush()
            else:
                # Regular file handling for non-media files
                file_path = os.path.join(self.save_path, file_info.file_path(file_index))
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'wb') as f:
                    f.seek(offset)
                    f.write(piece)

    def map_piece_to_files(self, piece_index, piece_size, file_info):
        files = {}
        piece_offset = piece_index * piece_size
        remaining_size = piece_size
        
        for i in range(file_info.num_files()):
            file_size = file_info.file_size(i)
            file_offset = file_info.file_offset(i)
            
            if file_offset + file_size > piece_offset:
                # This file contains data from this piece
                start = max(0, piece_offset - file_offset)
                size = min(remaining_size, file_size - start)
                files[i] = (start, size)
                
                remaining_size -= size
                if remaining_size <= 0:
                    break
                
        return files

    def close_file(self, index):
        if index in self.ffmpeg_processes:
            self.ffmpeg_processes[index].stdin.close()
            self.ffmpeg_processes[index].wait()
            del self.ffmpeg_processes[index]
            del self.buffers[index]

class TorrentDownloader:
    def __init__(self):
        self.session = lt.session()
        self.session.add_extension('ut_metadata')
        self.session.add_extension('ut_pex')
        self.handles = {}
        self.storage = None

    def add_torrent(self, magnet_link, movie_key):
        params = lt.parse_magnet_uri(magnet_link)
        save_path = f'/home/data/movies/{movie_key}/'
        
        self.storage = StreamingStorage(save_path)
        params.storage = self.storage
        params.storage_mode = lt.storage_mode_t.storage_mode_sparse
        
        handle = self.session.add_torrent(params)
        self.handles[movie_key] = handle
        self.storage.current_handle = handle
        
        # Initialize files
        torrent_info = handle.get_torrent_info()
        for i in range(torrent_info.num_files()):
            self.storage.initialize_file(i, handle)
        
        return handle

    def remove_torrent(self, movie_key):
        handle = self.handles.get(movie_key)
        if handle:
            torrent_info = handle.get_torrent_info()
            for i in range(torrent_info.num_files()):
                self.storage.close_file(i)
            self.session.remove_torrent(handle)

downloader = TorrentDownloader()

downloader.add_torrent(
"""magnet:?xt=urn:btih:C7C6FC39B7CCA0CAE1F65F166179F10C4FDC7347&dn=The+Gutter+2024+1080p+WEB-DL+HEVC+x265+5.1+BONE&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Fopentracker.io%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.dler.org%3A6969%2Fannounce&tr=udp%3A%2F%2Fr.l5.ca%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.dler.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fopen.stealth.si%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2F&tr=http%3A%2F%2Ftracker.bt4g.com%3A2095%2Fannounce&tr=udp%3A%2F%2Ftracker.torrent.eu.org%3A451%2Fannounce&tr=https%3A%2F%2Ftracker.gcrenwp.top%3A443%2Fannounce&tr=udp%3A%2F%2Ftracker.0x7c0.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fttk2.nbaonlineservice.com%3A6969%2Fannounce&tr=udp%3A%2F%2Fbandito.byterunner.io%3A6969%2Fannounce&tr=udp%3A%2F%2Fevan.im%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=http%3A%2F%2Ftracker.openbittorrent.com%3A80%2Fannounce&tr=udp%3A%2F%2Fopentracker.i2p.rocks%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.internetwarriors.net%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce&tr=udp%3A%2F%2Fcoppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.zer0day.to%3A1337%2Fannounce""", "na")

sleep(50)
