from django.urls import path

from . import views


urlpatterns = [  # Instructs the client where to get HTML templates
    path("", views.index, name="index"),
]