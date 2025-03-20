from shared.celeryconfig import app as celery_app
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import views

urlpatterns = [
    # path('', health_check, name='health_check'),
    path('search/', views.search_torrents, name='search-torrents'),
    path('download/<str:torrent_id>/', views.download_torrent, name='download_torrent'),
]
