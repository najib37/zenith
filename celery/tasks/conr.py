
import asyncio
from enum import Enum
import os
from signal import SIGSTOP, SIGCONT
from time import sleep, time
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
            print("~" * 20)
            print("~" * 20)
            print(f"size: {converted_size}")
            print("Progress: ", progress)
            print(f"filename: {self.input_file}")
            print(f"Downloading:{handle.status().progress * 100}% - Download Rate:{handle.status().download_rate / 1024}KB/s")
            print(f"Downloaded {donloaded_size / (1024 * 1024)}MB {donloaded_size} bytes")
            print("~" * 20)
            print("~" * 20)
            if converted_size  >= donloaded_size + (donloaded_size * 0.1): 
                process.send_signal(SIGSTOP)
                while converted_size  >= donloaded_size + (donloaded_size * 0.1): 
                    print("Waiting for download to catch up...")
                    sleep(1)
            process.send_signal(SIGCONT)

    def wait_file_creation(self, file, timeout=10):
        while not os.path.exists(file):
            # if timeout <= 0:
            #
            # timeout -= 1
            sleep(1)

    def start_conversion(self, handler):
        if self.ffmpeg is not None:
            print("FFmpeg process already initialized.")
            return
        try:
            # self.wait_file_creation(self.input_file)
            sleep(5)
            self.ffmpeg = (
                FFmpeg()
                .option('y')  # Overwrite output files
                .input(self.input_file)
                .output(
                    f'{self.output_path}/1080/1080p.m3u8',
                    {
                        'map': ['0:v', '0:a'],
                        'c:v': 'copy',      # Copy video codec
                        'c:a': 'copy',      # Copy audio codec
                        'sc_threshold': '0',
                        'g': '48',
                        'keyint_min': '48',
                        'hls_time': '6',
                        'hls_list_size': '0',
                        'hls_flags': 'independent_segments+delete_segments',
                        'hls_segment_type': 'mpegts',
                        'hls_segment_filename': f'{self.output_path}/1080/1080p_%03d.ts',
                        'var_stream_map': 'v:0,a:0'
                    }
                )
                .output(
                    f'{self.output_path}/720/720p.m3u8',
                    {
                        'map': ['0:v', '0:a'],
                        'c:v': 'libx264',
                        'c:a': 'aac',
                        'b:a': '128k',
                        'ar': '48000',
                        'preset': 'veryfast',
                        'crf': '23',
                        'vf': 'scale=-2:720',
                        'sc_threshold': '0',
                        'g': '48',
                        'keyint_min': '48',
                        'hls_time': '6',
                        'hls_list_size': '0',
                        'hls_flags': 'independent_segments+delete_segments',
                        'hls_segment_type': 'mpegts',
                        'hls_segment_filename': f'{self.output_path}/720/720p_%03d.ts',
                        'var_stream_map': 'v:0,a:0'
                    }
                )
                .output(
                    f'{self.output_path}/144/144p.m3u8',
                    {
                        'map': ['0:v', '0:a'],
                        'c:v': 'libx264',
                        'c:a': 'aac',
                        'b:a': '64k',
                        'ar': '44100',
                        'preset': 'veryfast',
                        'crf': '28',
                        'vf': 'scale=-2:144',
                        'sc_threshold': '0',
                        'g': '48',
                        'keyint_min': '48',
                        'hls_time': '6',
                        'hls_list_size': '0',
                        'hls_flags': 'independent_segments+delete_segments',
                        'hls_segment_type': 'mpegts',
                        'hls_segment_filename': f'{self.output_path}/144/144p_%03d.ts',
                        'var_stream_map': 'v:0,a:0'
                    }
                )
            )
            self.set_watcher(handler)
            self.ffmpeg.execute()

        except Exception as e:
            print(f"Error initializing FFmpeg: {e}")
            return

# async def main():
#     input_file = "/home/data/hls/na.mkv"
#     output_path = "/home/data/hls/na/"
#     converter = Converter(input_file, output_path)
#     await converter.start_conversion()
#     # while True:
#     #     print("Starting conversion...")
#     #     try:
#     #         await converter.start_conversion()
#     #     except Exception as e:
#     #         print(f"Error starting conversion: {e}")
#     #         continue
#     #     await asyncio.sleep(1)
#
# if __name__ == "__main__":
#     asyncio.run(main())
