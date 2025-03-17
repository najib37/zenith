from celery import Celery
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import py1337x

# TODO: convert this to a class based view

torrents = py1337x.Py1337x()

app = Celery (
    'tasks',
    backend='redis://localhost:6060',
    broker="amqp://userf:userd@localhost:5672"
)


@api_view(['GET'])
def search_torrents(request):
    movie_name = request.query_params.get('q', '')
    if not movie_name:
        return Response(
            {'error': 'Movie name is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        results = torrents.search(f"{movie_name} 1080", sort_by=py1337x.sort.SEEDERS).to_dict()
        return Response({
            'query': movie_name,
            'results': results['items'][:2] if results else []
        })
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
            args=[magnet_link, torrent_id]
        )
        
        return Response({
            'status': 'download_started',
            'torrent': result.get(),
            "info": info.to_dict()
        })
    except Exception as e:

        print("________________________________");
        print(f"download error {e}")
        print("________________________________");

        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
