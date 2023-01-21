from django.contrib import admin
from django.urls import include, path

urlpatterns = [  # Instructs the client where to get HTML templates
    path("server/", include("serverSocket.urls")),
    path("admin/", admin.site.urls),
]
