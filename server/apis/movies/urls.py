from shared.celeryconfig import app as celery_app
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from . import views

urlpatterns = [
    path('search', views.query_movies, name='query_movies'),
    path('detail/<int:movie_id>', views.movie_info, name='movie_info'),
    path('popular', views.popular_movies, name='popular_movies'),
]
