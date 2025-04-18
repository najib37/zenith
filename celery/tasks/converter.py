import asyncio
import json
import os
import signal
from enum import Enum
from time import sleep, time

import m3u8
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


class ConverterStatus(Enum):
    IDLE = "idle"
    CONVERTING = "converting"
    PAUSED = "paused"
    DONE = "done"
    DOWNLDED = "downloaded"

    def __init__(self, status: str):
        self.status = status


def convert_time(sec):
    return f"{int(sec //3600):02d}:{int((sec%3600)//60):02d}:{int(sec%60):02d}"


class Stream:

    def __init__(self, input_file, output_path, resulotion, none_corupt_duration=0):
        self.status = ConverterStatus.IDLE
        self.input_file = input_file
        self.output_path = output_path
        self.resulotion = resulotion
        self.none_corupt_duration = none_corupt_duration

        self.process = None
        self.current_segment = 0
        self.segment_duration = 0
        self.start_time = 0

    def calculate__segment(self):
        pass

    def attempt_restart(self, new_none_corupt_duration):
        if self.is_running() or new_none_corupt_duration <= 0:
            return

        self.none_corupt_duration = new_none_corupt_duration
        # self.start_time = self.none_corupt_duration
        # self.none_corupt_duration = new_none_corupt_duration - self.none_corupt_duration
        self.start()

    # def time_convert(self, sec):
    #     return time.strftime("%H:%M:%S", time.gmtime(sec))

    def start(self):

        if self.is_running():
            return
        playlist_path = f"{self.output_path}/{self.resulotion.prefix}/{self.resulotion.prefix}.m3u8"
        start_time = 0
        try:
            playlist = m3u8.load(playlist_path)
            start_time = sum(segment.duration for segment in playlist.segments)
        except :
            start_time  = 0

        print("*/" * 50)
        print("*/" * 50)
        print(f"Playlist path: {playlist_path}")
        print(f"non corupt: {self.none_corupt_duration}")
        print(f"Total duration: {start_time}")
        print("*/" * 50)
        print("*/" * 50)

        start_time = convert_time(start_time)
        convert_duration = convert_time(self.none_corupt_duration)

        self.process = (
            ffmpeg.input(self.input_file, ss=start_time)
            .filter("scale", self.resulotion.width, self.resulotion.height)
            .output(
                playlist_path,
                to=convert_duration,
                format="hls",
                hls_time=10,
                hls_list_size=0,
                hls_playlist_type='event',
                hls_segment_filename=f"{self.output_path}/{self.resulotion.prefix}/{self.resulotion.prefix}_%3d.ts",
                hls_flags="append_list+omit_endlist",
                # hls_flags="independent_segments",
                # start_number = 0,
                vcodec="libx264",
                acodec="aac",
                preset="fast",
                tune="film",
                crf=23,
                threads=4,
                video_bitrate=self.resulotion.bitrate,
                maxrate=self.resulotion.bitrate,
                bufsize="6M",
                audio_bitrate="192k",
                level="4.0",
                map="0:a:0?",
            )
            .run_async(quiet=True)
        )

        # self.current_segment = self.current_segment + self.none_corupt_duration // 10

        # self.status = ConverterStatus.CONVERTING

    def is_running(self):
        return self.process and self.process.pid and self.process.poll() is None

    # def create(self):
    #     # TODO: create the palylist with zero segments
    #     pass
    #
    # def stop(self):
    #     if self.status != ConverterStatus.CONVERTING:
    #         return
    #     if self.process and self.process.pid:
    #         self.process.terminate()
    #         try:
    #             self.process.wait(timeout=10)
    #         except TimeoutError:
    #             print(f"Stream took too long to stop, forcing kill")
    #             return
    #         self.status = ConverterStatus.DONE
    #
    # def pause(self):
    #     if self.status != ConverterStatus.CONVERTING:
    #         return
    #     if self.process and self.process.pid:
    #         os.kill(self.process.pid, signal.SIGSTOP)
    #     self.status = ConverterStatus.PAUSED
    #
    # def resume(self):
    #     if self.status != ConverterStatus.PAUSED:
    #         return
    #     if self.process and self.process.pid:
    #         os.kill(self.process.pid, signal.SIGCONT)
    #     self.status = ConverterStatus.CONVERTING


class VideoConverter:
    def __init__(self, input_file, output_path, movie_key):
        self.streams = {}
        self.input_file = input_file
        self.output_path = f"{output_path}/{movie_key}"
        self.duration = self.get_video_duration(input_file)
        self.none_corupt_duration = 0
        self.status = ConverterStatus.IDLE
        os.makedirs(f"{self.output_path}/1080/", exist_ok=True)
        os.makedirs(f"{self.output_path}/720/", exist_ok=True)
        os.makedirs(f"{self.output_path}/144/", exist_ok=True)

    def check_severe_corruption(
        self,
        start_time="00:00:00",
        chunk_duration="00:00:10",
        bytestream_threshold=-5,
    ):

        # start_time = ffmpeg.parse_time(start_time)

        process = (
            ffmpeg.input(self.input_file, ss=start_time)
            .output("null", format="null", t=chunk_duration)
            .global_args("-v", "error", "-xerror")  # BUG: -xerror
            .run_async(quiet=True)
        )

        process.wait()
        _, stderr = process.communicate()
        for line in stderr.decode("utf-8").splitlines():
            # print("**" * 50)
            # print(line)
            # print("**" * 50)
            if "error while decoding MB" in line:
                bytestream_val = int(line.split("bytestream")[-1])
                if bytestream_val < bytestream_threshold:
                    return True
        return False

    def update_none_corupt_duration(self):

        if not self.check_severe_corruption(convert_time(self.none_corupt_duration), "00:01:00"):
            self.none_corupt_duration = self.none_corupt_duration + 60

    def start_conversion(self):
        # self.create_playlist()

        if not self.is_ready_to_convert() or self.none_corupt_duration <= 0:
            return

        for res in VideoResulotion:
            if res.prefix in self.streams:
                self.streams[res.prefix].attempt_restart(self.none_corupt_duration)
                continue
            stream = Stream(self.input_file, self.output_path, res)
            stream.attempt_restart(self.none_corupt_duration)
            self.streams[res.prefix] = stream
        # self.status = ConverterStatus.CONVERTING

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
