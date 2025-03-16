import asyncio
import signal
import os
import json
from time import sleep
import ffmpeg
import m3u8

class VideoConverter:
    def __init__(self):
        self.process = None
        self.input_file = "/home/data/hls/na.mkv"
        self.output_path = "/home/data/hls/najib"
        self.state_file = f"{self.output_path}/converter_state.json"
        self.is_paused = False
        self.current_segment = 0
        self.load_state()
        
    def load_state(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.current_segment = state.get('segment', 0)
        except Exception as e:
            print(f"Error loading state: {e}")

    def save_state(self):
        try:
            with open(self.state_file, 'w') as f:
                json.dump({'segment': self.current_segment}, f)
        except Exception as e:
            print(f"Error saving state: {e}")

    def start_conversion(self):
        os.makedirs(f"{self.output_path}/1080/", exist_ok=True)
        os.makedirs(f"{self.output_path}/720/", exist_ok=True)
        
        # Calculate start time based on last processed segment
        start_time = self.current_segment * 10  # Since hls_time=10

        full_hd_stream = (
            ffmpeg
            .input(self.input_file, ss=start_time)
            .filter('scale', 1920, 1080)
            .output(
                f"{self.output_path}/1080/playlist.m3u8",
                format='hls',
                hls_time=5,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/1080/segment_%03d.ts",
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
                profile='high',
                level='4.0',
            )
            .run_async()
        )
        hd_stream = (
            ffmpeg
            .input(self.input_file, ss=start_time)
            .filter('scale', 1280, 720)
            .output(
                f"{self.output_path}/720/playlist.m3u8",
                format='hls',
                hls_time=5,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/720/segment_%03d.ts",
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
                profile='high',
                level='4.0',
            )
            .run_async()
        ) 
        sleep(10)
        # playlist1 = m3u8.load(f"{self.output_path}/1080/playlist.m3u8")
        # playlist2 = m3u8.load(f"{self.output_path}/720/playlist.m3u8")
        # master_playlist = playlist1.dumps() + playlist2.dumps()
        master_playlist_content = (
            "#EXTM3U\n"
            "#EXT-X-STREAM-INF:BANDWIDTH=5000000,RESOLUTION=1920x1080\n"
            "1080/playlist.m3u8\n"
            "#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720\n"
            "720/playlist.m3u8\n"
        )
        with open(f"{self.output_path}/master_playlist.m3u8", 'w') as f:
            f.write(master_playlist_content)

        # self.process = await asyncio.create_subprocess_exec(
        #     *args,
        #     # stdout=asyncio.subprocess.PIPE,
        #     # stderr=asyncio.subprocess.PIPE
        # )

        print(f"Conversion started from segment {self.current_segment}. Press Ctrl+C to pause/resume.")

    # async def pause(self):
    #     if self.process and not self.is_paused:
    #         self.is_paused = True
    #         # Get the latest segment number from the filesystem
    #         segments = [f for f in os.listdir(self.output_path) if f.endswith('.ts')]
    #         if segments:
    #             latest_segment = max([int(s.split('_')[1].split('.')[0]) for s in segments])
    #             self.current_segment = latest_segment
    #             self.save_state()
    #
    #         await self.stop()
    #         print("Conversion paused")
    #
    # def resume(self):
    #     if self.is_paused:
    #         self.is_paused = False
    #         self.start_conversion()
    #         print("Conversion resumed")
    #
    #  def stop(self):
    #     if self.process:
    #         try:
    #             self.process.terminate()
    #             try:
    #                 # await asyncio.wait_for(self.process.wait(), timeout=5.0)
    #                 pass
    #             except asyncio.TimeoutError:
    #                 self.process.kill()
    #                 # await self.process.wait()
    #         except Exception as e:
    #             print(f"Error stopping conversion: {e}")

def main():
    converter = VideoConverter()
    
    # def signal_handler(signum, frame):
    #     if converter.is_paused:
    #         asyncio.create_task(converter.resume())
    #     else:
    #         asyncio.create_task(converter.pause())
    #
    # Set up signal handler for SIGINT (Ctrl+C)
    # signal.signal(signal.SIGINT, signal_handler)
    
    converter.start_conversion()
    # sleep(10)
    # await converter.pause()
    # # sleep(10)
    # await converter.resume()
    # Wait for the process to complete
    # if converter.process:
    #     converter.process.wait()

if __name__ == "__main__":
    main()
