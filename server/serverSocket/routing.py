from django.urls import re_path

from . import consumers

websocket_urlpatterns = [  # When a client connects to /server/, create them a consumer
    re_path(r"ws/server/", consumers.SocketConsumer.as_asgi()),
]