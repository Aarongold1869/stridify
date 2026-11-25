"""
URL configuration for Stridify project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

def backlink_page(request):
    return HttpResponse('''<!DOCTYPE html>
<html>
<head><title>Stridify</title></head>
<body>
<h1>Stridify - Music Running Playlists</h1>
<p>Personalized playlists based on your running cadence.</p>
<p>BPM data powered by <a href="https://www.getsongbpm.com">GetSongBPM</a></p>
</body>
</html>''', content_type='text/html')

def about_page(request):
    return HttpResponse('''<!DOCTYPE html>
<html>
<head><title>About Stridify</title></head>
<body>
<h1>About Stridify</h1>
<p>Stridify creates personalized music playlists synchronized to your running cadence.</p>
<h2>Credits</h2>
<p>BPM and audio metadata provided by <a href="https://www.getsongbpm.com">GetSongBPM</a></p>
</body>
</html>''', content_type='text/html')

urlpatterns = [
    path('', backlink_page),
    path('about/', about_page),
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('api-auth/', include('rest_framework.urls')),
]
