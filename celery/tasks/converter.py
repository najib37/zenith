import asyncio
import signal
import os
import json
from time import sleep
import ffmpeg

class VideoConverter:
    def __init__(self):
        self.process = None
        self.input_file = "/home/data/na.mkv"
        self.output_path = "/home/data/hls"
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

    async def start_conversion(self):
        os.makedirs(self.output_path, exist_ok=True)
        
        # Calculate start time based on last processed segment
        start_time = self.current_segment * 10  # Since hls_time=10

        args = (
            ffmpeg
            .input(self.input_file, ss=start_time)
            .output(
                f"{self.output_path}/playlist.m3u8",
                format='hls',
                hls_time=10,
                hls_list_size=0,
                hls_segment_filename=f"{self.output_path}/segment_%03d.ts",
                hls_flags='independent_segments',
                start_number=self.current_segment,
                acodec='aac',
                vcodec='h264'
            )
            .compile()
        )
        
        self.process = await asyncio.create_subprocess_exec(
            *args,
            # stdout=asyncio.subprocess.PIPE,
            # stderr=asyncio.subprocess.PIPE
        )
        print(f"Conversion started from segment {self.current_segment}. Press Ctrl+C to pause/resume.")

    async def pause(self):
        if self.process and not self.is_paused:
            self.is_paused = True
            # Get the latest segment number from the filesystem
            segments = [f for f in os.listdir(self.output_path) if f.endswith('.ts')]
            if segments:
                latest_segment = max([int(s.split('_')[1].split('.')[0]) for s in segments])
                self.current_segment = latest_segment
                self.save_state()
            
            await self.stop()
            print("Conversion paused")

    async def resume(self):
        if self.is_paused:
            self.is_paused = False
            await self.start_conversion()
            print("Conversion resumed")

    async def stop(self):
        if self.process:
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except Exception as e:
                print(f"Error stopping conversion: {e}")

async def main():
    converter = VideoConverter()
    
    def signal_handler(signum, frame):
        if converter.is_paused:
            asyncio.create_task(converter.resume())
        else:
            asyncio.create_task(converter.pause())
        
    # Set up signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    await converter.start_conversion()
    # sleep(10)
    # await converter.pause()
    # # sleep(10)
    # await converter.resume()
    # Wait for the process to complete
    if converter.process:
        await converter.process.wait()

if __name__ == "__main__":
    asyncio.run(main())
