
from enum import Enum
import os
from signal import SIGSTOP, SIGCONT
from time import sleep
from ffmpeg import FFmpeg

class ConverterType(Enum):
    MKV = "mkv"
    MP4 = "mp4"

class Converter:
    def __init__(self, input_file, output_path):
        self.ffmpeg = None
        self.process = None
        self.output_path = output_path
        self.input_file = input_file
        self.type = ConverterType.MKV
        os.makedirs(f"{self.output_path}/1080", exist_ok=True)
        os.makedirs(f"{self.output_path}/720", exist_ok=True)
        os.makedirs(f"{self.output_path}/144", exist_ok=True)

    def stop_conversion(self):
        if self.ffmpeg is not None and self.ffmpeg._process:
            self.ffmpeg.terminate()
            self.ffmpeg = None
        else:
            print("FFmpeg process not initialized.")
            return

    def get_dir_size(self, path):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
        return total

    def set_watcher(self, handle):
        if self.ffmpeg is None:
            print("FFmpeg process not initialized.")
            return

        @self.ffmpeg.on('progress')
        def progress(progress):
            nonlocal self
            nonlocal handle
            process = self.ffmpeg._process
            if not process:
                print("FFmpeg process not running.")
                return
            converted_size = self.get_dir_size(f"{self.output_path}/1080")
            donloaded_size = handle.status().total_done
            if converted_size  >= donloaded_size + (donloaded_size * 0.2): 
                process.send_signal(SIGSTOP)
                while converted_size  >= donloaded_size + (donloaded_size * 0.2): 
                    print("~" * 20)
                    print("~" * 20)
                    print("Waiting for download to catch up...")
                    print(f"size: {converted_size}")
                    print("Progress: ", progress)
                    print(f"filename: {self.input_file}")
                    print(f"Downloading:{handle.status().progress * 100}% - Download Rate:{handle.status().download_rate / 1024}KB/s")
                    print(f"Downloaded {donloaded_size / (1024 * 1024)}MB {donloaded_size} bytes")
                    print("~" * 20)
                    print("~" * 20)
                    sleep(1)
            process.send_signal(SIGCONT)

    def wait_file_creation(self, file, handle, timeout=120):

        print(f"total done: {handle.status().total_done}")
        t = timeout

        while handle.status().progress < 0.01 and t > 0:
            t -= 0.5
            sleep(0.5)

        while not os.path.exists(file) and timeout > 0:
            timeout -= 0.5
            sleep(0.5)

    def start_conversion(self, handler):
        if self.ffmpeg is not None:
            print("FFmpeg process already initialized.")
            return
        try:
            self.wait_file_creation(self.input_file, handler)
            self.ffmpeg = (
                FFmpeg()
                .option('y')  # Overwrite output files
                .input(self.input_file)
                .output(
                    f'{self.output_path}/1080/1080p.m3u8',
                    {
                        'map': ['0:v:0', '0:a:0'], # Map first video and first audio stream
                        'c:v': 'copy',      # Copy video codec
                        'c:a': 'copy',      # Copy audio codec
                        # Options like 'sc_threshold', 'g', 'keyint_min' are ignored with 'c:v copy'
                        # 'vf' (video filter) is also ignored with 'c:v copy'
                        'hls_time': '6',
                        'hls_list_size': '0',
                        'hls_flags': 'independent_segments+delete_segments',
                        'hls_segment_type': 'mpegts',
                        'hls_segment_filename': f'{self.output_path}/1080/1080p_%03d.ts',
                        # 'var_stream_map' is not needed here as master playlist is manually created
                    }
                )
                .output(
                    f'{self.output_path}/720/720p.m3u8',
                    {
                        'map': ['0:v:0', '0:a:0'], # Map first video and first audio stream
                        'c:v': 'libx264',
                        'c:a': 'aac',
                        'b:a': '128k',
                        'ar': '48000',
                        'preset': 'veryfast',
                        'crf': '23',
                        'vf': 'scale=-2:720',
                        'sc_threshold': '0',
                        'g': '48', # Keyframe interval
                        'keyint_min': '48', # Minimum keyframe interval
                        'hls_time': '6',
                        'hls_list_size': '0',
                        'hls_flags': 'independent_segments+delete_segments',
                        'hls_segment_type': 'mpegts',
                        'hls_segment_filename': f'{self.output_path}/720/720p_%03d.ts',
                        # 'var_stream_map' is not needed here
                    }
                )
                .output(
                    f'{self.output_path}/144/144p.m3u8',
                    {
                        'map': ['0:v:0', '0:a:0'], # Map first video and first audio stream
                        'c:v': 'libx264',
                        'c:a': 'aac',
                        'b:a': '64k',
                        'ar': '44100',
                        'preset': 'veryfast',
                        'crf': '28',
                        'vf': 'scale=-2:144',
                        'sc_threshold': '0',
                        'g': '48', # Keyframe interval
                        'keyint_min': '48', # Minimum keyframe interval
                        'hls_time': '6',
                        'hls_list_size': '0',
                        'hls_flags': 'independent_segments+delete_segments',
                        'hls_segment_type': 'mpegts',
                        'hls_segment_filename': f'{self.output_path}/144/144p_%03d.ts',
                        # 'var_stream_map' is not needed here
                    }
                )
            )
            self.set_watcher(handler)
            self.create_master()
            self.ffmpeg.execute()

        except Exception as e:
            print(f"Error initializing FFmpeg: {e}")
            return

    def create_master(self):
        try:
            with open(f"{self.output_path}/master.m3u8", "w") as f:
                f.write("#EXTM3U\n")
                f.write("#EXT-X-VERSION:3\n")
                f.write("#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080\n")
                f.write("1080/1080p.m3u8\n")
                f.write("#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=1280x720\n")
                f.write("720/720p.m3u8\n")
                f.write("#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=640x360\n")
                f.write("144/144p.m3u8\n")
        except Exception as e:
            print(f"Error creating master playlist: {e}")

