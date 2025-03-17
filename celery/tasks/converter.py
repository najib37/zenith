import asyncio
import signal
import os
import json
from time import sleep
import ffmpeg

class VideoConverter:
    def __init__(self, input_file, output_path, movie_key):
        self.process = None
        self.streams = {}
        self.input_file = input_file
        self.output_path = f"{str(movie_key)}/{output_path}"
        self.is_stated = False
        self.current_segment = 0
        self.duration = self.get_video_duration(input_file)
        os.makedirs(f"{self.output_path}/1080/", exist_ok=True)
        os.makedirs(f"{self.output_path}/720/", exist_ok=True)

    def file_exists(self, file_path):
        if not os.path.exists(self.input_file):
            return False
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)

    def is_ready_to_convert(self):
        return self.file_exists(self.input_file) and self.duration > 0

    def get_video_duration(self, file_path):
        if not self.file_exists(file_path): return 0
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe['format']['duration'])
            print("----------------------------")
            print(f"Duration: {duration}")
            print("----------------------------")
            return duration
        except ffmpeg.Error:
            return 0

    def create_playlist(self):
        with open(f"{self.output_path}/master.m3u8", 'w') as f:
            f.write(
                "#EXTM3U\n"
                "#EXT-X-VERSION:3\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080\n"
                "1080.m3u8\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720\n"
                "720.m3u8\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=256x144\n"
                "144.m3u8\n"
            )

    def start_conversion(self):
        start_time = 0

        self.streams['sd'] = (
            ffmpeg
            .input(self.input_file, ss=start_time)
            .filter('scale', 256, 144)
            .output(
                f"{self.output_path}/144.m3u8",
                format='hls',
                hls_time=5,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/144_%03d.ts",
                hls_flags='independent_segments',
                start_number=self.current_segment,
                vcodec='libx264',
                acodec='aac',
                preset='fast',
                tune='film',
                crf=23,
                threads=4,

                video_bitrate='3M',
                maxrate='3M',
                bufsize='6M',
                audio_bitrate='192k',
                level='4.0',
            )
            .run_async()
        ) 

        self.streams['fhd'] = (
            ffmpeg
            .input(self.input_file, ss=start_time)
            .filter('scale', 1920, 1080)
            .output(
                f"{self.output_path}/1080.m3u8",
                format='hls',
                hls_time=5,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/1080_%03d.ts",
                hls_flags='independent_segments',
                start_number=self.current_segment,
                vcodec='libx264',
                acodec='aac',
                preset='fast',
                tune='film',
                crf=23,
                threads=4,

                video_bitrate='3M',
                maxrate='3M',
                bufsize='6M',
                audio_bitrate='192k',
                level='4.0',
            )
            .run_async()
        )
        self.streams['hd'] = (
            ffmpeg
            .input(self.input_file, ss=start_time)
            .filter('scale', 1280, 720)
            .output(
                f"{self.output_path}/720.m3u8",
                format='hls',
                hls_time=5,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/720_%03d.ts",
                hls_flags='independent_segments',
                start_number=self.current_segment,
                vcodec='libx264',
                acodec='aac',
                preset='fast',
                tune='film',
                crf=23,
                threads=4,

                video_bitrate='3M',
                maxrate='3M',
                bufsize='6M',
                audio_bitrate='192k',
                level='4.0',
            )
            .run_async()
        ) 
        self.create_playlist()

        print(f"Conversion started from segment {self.current_segment}. Press Ctrl+C to pause/resume.")

def main():
    converter = VideoConverter(
        input_file="/home/data/hls/na.mkv",
        output_path="/home/data/hls/najib",
        movie_key=55
    )

if __name__ == "__main__":
    main()
