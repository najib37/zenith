import asyncio
import json
import os
import signal
from enum import Enum
from time import sleep

import ffmpeg


class VideoResulotion(Enum):
    SD = ("144", 256, 144, "1M")
    HD = ("720", 1280, 720, "3M")
    FHD = ("1080", 1920, 1080, "5M")

    def __init__(
        self,
        prefix: str,
        width: int,
        height: int,
        bitrate: str,
    ):
        self.prefix = prefix
        self.width = width
        self.height = height
        self.bitrate = bitrate
        # self.status = ConverterStatus.IDLE
        self.segment = 0


class ConverterStatus(Enum):
    IDLE = "idle"
    CONVERTING = "converting"
    PAUSED = "paused"
    DONE = "done"
    DOWNLDED = "downloaded"

    def __init__(self, status: str):
        self.status = status


class Stream:

    def __init__(self, input_file, output_path, resolution):
        self.status = ConverterStatus.IDLE
        self.segment = 0
        self.process = None
        self.start_time = 0
        self.input_file = input_file
        self.output_path = output_path

    def start(self, res: VideoResulotion):

        if self.status == ConverterStatus.CONVERTING:
            return
        self.process = (
            ffmpeg.input(self.input_file, ss=self.start_time)
            .filter("scale", res.width, res.height)
            .output(
                f"{self.output_path}/{res.prefix}/{res.prefix}.m3u8",
                format="hls",
                hls_time=10,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/{res.prefix}/{res.prefix}_%03d.ts",
                hls_flags="independent_segments",
                start_number=0,
                vcodec="libx264",
                acodec="aac",
                preset="fast",
                tune="film",
                crf=23,
                threads=4,
                video_bitrate=res.bitrate,
                maxrate=res.bitrate,
                bufsize="6M",
                audio_bitrate="192k",
                level="4.0",
                map="0:a:0?",
            )
            .run_async()
        )

        self.status = ConverterStatus.CONVERTING

    def create(self):
        # TODO: create the palylist with zero segments
        pass

    def stop(self):
        if self.status != ConverterStatus.CONVERTING:
            return
        if self.process and self.process.pid:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except TimeoutError:
                print(f"Stream took too long to stop, forcing kill")
                return
            self.status = ConverterStatus.DONE

    def pause(self):
        if self.status != ConverterStatus.CONVERTING:
            return
        if self.process and self.process.pid:
            os.kill(self.process.pid, signal.SIGSTOP)
        self.status = ConverterStatus.PAUSED

    def resume(self):
        if self.status != ConverterStatus.PAUSED:
            return
        if self.process and self.process.pid:
            os.kill(self.process.pid, signal.SIGCONT)
        self.status = ConverterStatus.CONVERTING


class VideoConverter:
    def __init__(self, input_file, output_path, movie_key):
        self.streams = {}
        self.input_file = input_file
        self.output_path = f"{output_path}/{movie_key}"
        self.duration = self.get_video_duration(input_file)
        self.status = ConverterStatus.IDLE
        os.makedirs(f"{self.output_path}/1080/", exist_ok=True)
        os.makedirs(f"{self.output_path}/720/", exist_ok=True)
        os.makedirs(f"{self.output_path}/144/", exist_ok=True)

    def check_severe_corruption(
        self,
        video_path,
        start_time="00:00:00",
        chunk_duration="00:00:10",
        bytestream_threshold=-6,
    ):
        process = (
            ffmpeg.input(video_path, ss=start_time)
            .output("null", format="null", t=chunk_duration)
            .global_args("-v", "error", "-xerror")  # BUG: -xerror
            .run_async(pipe_stdout=True, pipe_stderr=True, quiet=True)
        )

        _, stderr = process.communicate()
        for line in stderr.decode("utf-8").splitlines():
            print("==" * 50)
            print(line)
            print("==" * 50)
            if "error while decoding MB" in line:
                bytestream_val = int(line.split("bytestream")[-1])
                if bytestream_val < bytestream_threshold:
                    return True
        return False

    def start_conversion(self):
        # self.create_playlist()

        if self.status == ConverterStatus.CONVERTING or not self.is_ready_to_convert():
            return

        for res in VideoResulotion:
            stream = Stream(self.input_file, self.output_path, res)
            stream.start(res)
            self.streams[res.prefix] = stream
        self.status = ConverterStatus.CONVERTING

    def pause_conversion(self):
        print("Pause conversion")
        for stream in self.streams.values():
            stream.pause()
        self.status = ConverterStatus.PAUSED

    def resume_conversion(self):
        print("Resume conversion")
        for stream in self.streams.values():
            stream.resume()
        self.status = ConverterStatus.CONVERTING

    def stop_conversion(self):
        print("Stop conversion")
        for stream in self.streams.values():
            stream.stop()
        self.status = ConverterStatus.DONE

    def file_exists(self, file_path):
        if not os.path.exists(self.input_file):
            return False
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)

    def is_ready_to_convert(self):

        if self.duration == 0:
            self.duration = self.get_video_duration(self.input_file)

        return self.file_exists(self.input_file) and self.duration > 0

    def get_video_duration(self, file_path):
        if not self.file_exists(file_path):
            return 0
        try:
            probe = ffmpeg.probe(file_path)
            duration = float(probe["format"]["duration"])
            print("----------------------------")
            print(f"Duration: {duration}")
            print("----------------------------")
            return duration
        except ffmpeg.Error:
            return 0

    def create_playlist(self):
        with open(f"{self.output_path}/master.m3u8", "w") as f:
            f.write(
                "#EXTM3U\n"
                "#EXT-X-VERSION:3\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080\n"
                "1080/1080.m3u8\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720\n"
                "720/720.m3u8\n"
                "#EXT-X-STREAM-INF:BANDWIDTH=1000000,RESOLUTION=256x144\n"
                "144/144.m3u8\n"
            )


def main():
    converter = VideoConverter(
        input_file="/home/data/hls/na.mkv",
        output_path="/home/data/hls/najib",
        movie_key=55,
    )
    converter.start_conversion()

    sleep(10)

    print("*" * 100)
    print("*" * 100)
    converter.pause_conversion()

    sleep(10)

    print("*" * 100)
    print("*" * 100)
    converter.resume_conversion()

    sleep(10)

    print("*" * 100)
    print("*" * 100)
    converter.stop_conversion()


if __name__ == "__main__":
    main()
