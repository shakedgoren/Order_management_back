from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root_view(request):
    return JsonResponse({"message": "ג'חנון על גלגלים API is running 🥐 (Django)"})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_view, name='root'),
    path('', include('api.urls')),
]
