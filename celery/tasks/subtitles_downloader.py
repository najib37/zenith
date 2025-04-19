
import requests

class SubtitlesDownloader:
    API_URL = "https://api.opensubtitles.com/api/v1"
    LANGUAGES = ['fr', 'en', 'ar']
    HEADERS = {
        "Api-Key": API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "MovieAppv1.0"
    }

    @classmethod
    def get_sub_id(cls, movie_name):
        #delete .mkv from movie_name
        if movie_name.endswith(".mkv"):
            movie_name = movie_name[:-4]

        search_params = {
            "query": movie_name,
            "languages": ",".join(cls.LANGUAGES),
            "order_by": "download_count",
        }
        try:
            search_response = requests.get(
                f"{cls.API_URL}/subtitles", 
                params=search_params,
                headers=cls.HEADERS
            )
            search_response.raise_for_status()
            subtitles_info = {}
            results = search_response.json().get("data", [])
            # results = sorted(
            #     search_response.json().get("data", []),
            #     key=lambda x: x.get("attributes", {}).get("download_count", 0),
            #     reverse=True
            # )

            for subtitle in results:
                subtitle_id = subtitle.get("id")
                language = subtitle.get('attributes', {}).get("language", {})
                file_id = subtitle.get("attributes", {}).get("files", [{}])[0].get("file_id")
                file_name = subtitle.get("attributes", {}).get("files", [{}])[0].get("file_name")

                
                if not file_id:
                    continue
                
                if len(subtitles_info.keys()) >= 3:
                    break

                if language in cls.LANGUAGES:
                    if not subtitles_info.get(language, None):
                        subtitles_info[language]= {
                        "movie_name": movie_name,
                        "sub_name": file_name,
                        "id": subtitle_id,
                        "file_id": file_id
                    }

            print(f"Found subtitles: {subtitles_info}")
            return subtitles_info
        except Exception as e:
            print(f"Error downloading subtitles: {str(e)}")
            return {}

    @classmethod
    def download_sub(cls):
        # Download implementation here
        pass

