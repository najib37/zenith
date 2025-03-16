import os
import ffmpeg


def start_conversion(input_file, output_path, current_segment=0):
    os.makedirs(output_path, exist_ok=True)

    split = ffmpeg.input(input_file).filter_multi_output('split') 
    split0 = split.stream(0) 
    split1 = split[1]
    
    (
        ffmpeg
        .output(
            split0, split1,
            f'{output_path}/master.m3u8',
            # HLS specific settings
            f='hls',
            hls_time=2,
            hls_playlist_type='vod',
            hls_flags='independent_segments',
            hls_segment_type='mpegts',
            hls_segment_filename=f'{output_path}/stream_%v/data%02d.ts',
            # Stream mapping
            var_stream_map='v:0,a:0 v:1,a:0'
        )
        .overwrite_output()
        .run_async()
        .wait()
    )
    
    print(f"Conversion started from segment {current_segment}. Press Ctrl+C to pause/resume.")
    

start_conversion("/home/data/na.mkv", "/home/data/najib/", current_segment=0)
