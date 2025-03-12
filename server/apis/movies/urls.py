from shared.celeryconfig import app as celery_app
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import views

# @api_view(['GET'])
# def health_check(request):
#     result = celery_app.send_task('add', args=[4, 5])
#     print("____________________________")
#     print(result.get())
#     print("____________________________")
#     return Response({"status": "ok"})

urlpatterns = [
    # path('', health_check, name='health_check'),
    path('search/', views.search_torrents, name='search-torrents'),
    path('download/<str:torrent_id>/', views.download_torrent, name='download_torrent'),
]
