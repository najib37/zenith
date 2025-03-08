import ffmpeg

def get_video_duration(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration_seconds = float(probe['format']['duration'])
        duration_minutes = duration_seconds / 60
        return duration_minutes
    except ffmpeg.Error:
        return None

# You could add this to your TorrentDownloader class methods
def get_video_info(self, movie_key):
    handle = self.handles.get(movie_key)
    if not handle or not handle.is_seed():
        return None
        
    ti = handle.get_torrent_info()
    save_path = f'/home/data/movies/{movie_key}/'
    
    # Look for video files
    for i in range(ti.num_files()):
        file_name = ti.files().file_name(i)
        if file_name.lower().endswith(('.mp4', '.mkv', '.avi')):
            full_path = f"{save_path}/{file_name}"
            duration = get_video_duration(full_path)
            if duration:
                return {
                    'file_name': file_name,
                    'duration_minutes': round(duration, 2)
                }
    return None



