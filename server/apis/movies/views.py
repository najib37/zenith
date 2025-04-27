import logging

import requests
from celery import Celery
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# TODO: convert this to a class based view

app = Celery(
    "tasks",
    broker="amqp://userf:userd@rabbitmq:5672",
    queue="download_torrents",
    backend="redis://redis:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

headers = {
    "accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiNjg4YzIxMDY0ODVlOTg1MzQwOGE4YmQzZmMzOGMyMyIsIm5iZiI6MTc0NDM5MTI1MS4xODMsInN1YiI6IjY3Zjk0YzUzMWJjNjM5NTY2YWRhNDE4YiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.0G-7MTvuEvGS8yVjutuj9NMYiTHvvAsDFFDMCsAg2YU",
}


@api_view(["GET"])
def query_movies(request):
    movie_name = request.query_params.get("q", "")
    page = request.query_params.get("page", 1)
    if not movie_name:
        return Response(
            {"error": "Movie name is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        task = app.send_task(
            "download_movie_task",
            args=[movie_name],
            retry=False,
            queue="torrent_queue",
        )
        # params = {
        #     "query": movie_name,
        #     "include_adult": False,
        #     "language": "en-US",
        #     "page": page,
        # }
        # url = f"https://api.themoviedb.org/3/search/movie"
        # response = requests.get(url, headers=headers, params=params)
        return Response(
            {
                "query": movie_name,
                "info": task.get(),
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def movie_info(request, movie_id):
    if not movie_id:
        return Response(
            {"error": "Movie ID is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    cache_key = f"movie_info_{movie_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(
            {
                "movie_id": movie_id,
                "info": cached_data,
            }
        )

    try:

        moviedb_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        moviedb_response = requests.get(moviedb_url, headers=headers)
        moviedb_response.raise_for_status()
        imdb_id = moviedb_response.json().get("imdb_id")

        if not imdb_id:
            return Response(
                {"error": "IMDB ID not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        imdb_url = f"https://imdb236.p.rapidapi.com/imdb/{imdb_id}"
        imdb_response = requests.get(
            imdb_url,
            headers={
                "x-rapidapi-key": "8abb225a39msh1d2a397ef13d093p150511jsn9fe31a5e6efd",
            },
        )
        imdb_response.raise_for_status()
        data = imdb_response.json()
        if not data:
            return Response(
                {"error": "Movie not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        cast_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits"
        cast_response = requests.get(cast_url, headers=headers)
        cast_response.raise_for_status()

        cast_data = cast_response.json()
        if not cast_data:
            return Response(
                {"error": "Cast not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        cast = cast_data.get("cast", [])

        exclude_fields = {
            "cast",
            "genres",
            "directors",
            "writers",
            "filming_locations",
            "interests",
            "externalLinks",
            "grossWorldwide",
            "runtimeMinutes",
            "countriesOfOrigin",
            "budget",
            "productionCompanies",
        }
        imdb_data_filtered = {k: v for k, v in data.items() if k not in exclude_fields}
        actors = [c for c in cast if c and c["known_for_department"] == "Acting"][:10]
        imdb_data_filtered["cast"] = actors
        cache.set(cache_key, imdb_data_filtered, timeout=3600)
        return Response(
            {
                "movie_id": movie_id,
                "info": imdb_data_filtered,
            }
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def popular_movies(request):
    page = request.query_params.get("page", 1)
    try:
        cache_key = f"popular_movies_{page}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return Response(cached_response)
        url = f"https://api.themoviedb.org/3/movie/popular"
        params = {
            "language": "en-US",
            "page": page,
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        size = (
            0 if response.json()["results"] is None else len(response.json()["results"])
        )
        response = {"page": page, "size": size, "result": response.json()}
        cache.set(cache_key, response, timeout=3600)
        return Response(response)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# https://image.tmdb.org/t/p/w500/lurEK87kukWNaHd0zYnsi3yzJrs.jpg

# @api_view(['GET'])
# def download_torrent(request, torrent_id):
#     if not torrent_id:
#         return Response(
#             {'error': 'Torrent ID is required'},
#             status=status.HTTP_400_BAD_REQUEST
#         )
#     try:
#         # info = torrents.info(torrent_id=torrent_id)
#         # print("________________________________");
#         # print(f"info {info}")
#         # print("________________________________");
#         # magnet_link = info.magnet_link
#
#         result = app.send_task(
#             'download_torrents',
#             args=[magnet_link, torrent_id],
#             retry=False,
#             queue='torrent_queue',  # Different queue name
#         )
#
#         return Response({
#             'status': 'download_started',
#             'task_info': result.get(),
#             "torrent_inf": info.to_dict()
#         })
#     except Exception as e:
#
#         print("________________________________");
#         print(f"download error {e}")
#         print("________________________________");
#
#         return Response(
#             {'error': str(e)},
#             status=status.HTTP_500_INTERNAL_SERVER_ERROR
#         )
