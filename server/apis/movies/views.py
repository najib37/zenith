from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import py1337x

torrents = py1337x.Py1337x()

@api_view(['GET'])
def search_torrents(request):
    movie_name = request.query_params.get('q', '')
    if not movie_name:
        return Response(
            {'error': 'Movie name is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        results = torrents.search(movie_name, sort_by=py1337x.sort.SEEDERS)

        return Response({
            'query': movie_name,
            'results': results.to_dict()
        })
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def download_torrent(request):
    torrent_id = request.query_params.get('id', '')
    if not torrent_id:
        return Response(
            {'error': 'Torrent ID is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        info = torrents.info(torrent_id=torrent_id)
        magnet_link = info.magnet_link

        return Response({
            'torrent': magnet_link
        })
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
