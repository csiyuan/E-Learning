"""
ASGI config for elearning_platform project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
import django

# IMPORTANT: set Django settings BEFORE importing anything else
# this was tricky to figure out - had an import order error before adding this
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elearning_platform.settings")
django.setup()

# now we can import Django and Channels stuff
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from core.routing import websocket_urlpatterns

# this is important - it routes HTTP and WebSocket differently
# I learned that HTTP and WebSocket use different protocols
application = ProtocolTypeRouter({
    # normal HTTP requests go here
    "http": get_asgi_application(),
    # WebSocket connections go here
    # AuthMiddlewareStack gives us access to request.user in the consumer
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
