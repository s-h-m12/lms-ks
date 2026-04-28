import os
import django
from django.core.asgi import get_asgi_application


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lmspr.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from lmsapp import consumers
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler

django_asgi_app = ASGIStaticFilesHandler(get_asgi_application())

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/chat/<str:room_name>/', consumers.ChatConsumer.as_asgi()),
        ])
    ),
})
