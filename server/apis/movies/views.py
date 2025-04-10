from celery import Celery
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import py1337x
from py1337x.types import category, sort, order
import logging

# TODO: convert this to a class based view

torrents = py1337x.Py1337x()

app = Celery(
    'tasks',
    broker='amqp://userf:userd@rabbitmq:5672',
    queue='download_torrents',
    backend='redis://redis:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_torrent_info(torrent_id):
    try:
        info = torrents.info(torrent_id=torrent_id).to_dict()
        return info
    except Exception as e:
        logger.error(f"Error fetching torrent info: {e}")
        return None


@api_view(['GET'])
def search_torrents(request):
    movie_name = request.query_params.get('q', '')
    if not movie_name:
        return Response(
            {'error': 'Movie name is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # results = torrents.search(f"{movie_name} 1080", sort_by=py1337x.sort.SEEDERS, category=category.MOVIES).to_dict()
        # keys = [results['items'][i]['torrent_id'] for i in range(len(results['items']))]
        # info = [ torrents.info(torrent_id=key) for key in keys]
        # magnets = [magnet.magnet_link for magnet in info]



        task = app.send_task(
            'download_movie_task',
            args=[movie_name],
            retry=False,
            queue='torrent_queue',  # Different queue name
        )
        info = task.get()

        return Response({
            'query': movie_name,
            'info': info,
            # 'results': results['items'] if results else []
        })
    

    #     return Response({
    #         'query': movie_name,
    #         'results': results['items'] if results else []
    #     })
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def download_torrent(request, torrent_id):
    if not torrent_id:
        return Response(
            {'error': 'Torrent ID is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        info = torrents.info(torrent_id=torrent_id)
        print("________________________________");
        print(f"info {info}")
        print("________________________________");
        magnet_link = info.magnet_link

        result = app.send_task(
            'download_torrents',
            args=[magnet_link, torrent_id],
            retry=False,
            queue='torrent_queue',  # Different queue name
        )
        
        return Response({
            'status': 'download_started',
            'task_info': result.get(),
            "torrent_inf": info.to_dict()
        })
    except Exception as e:

        print("________________________________");
        print(f"download error {e}")
        print("________________________________");

        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
