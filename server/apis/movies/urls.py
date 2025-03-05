# from django.contrib import admin
# from django.urls import path, include
#
# urlpatterns = [
#     # path('admin/', admin.site.urls),
#     # path('api/movies/', include('apis.movies.urls')),
#
# ]
#
from shared.celeryconfig import app as celery_app
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def health_check(request):
    result = celery_app.send_task('add', args=[4, 5])
    print("____________________________")
    print(result.get())
    print("____________________________")
    return Response({"status": "ok"})

urlpatterns = [
    path('', health_check, name='health_check'),
]
