from django.urls import re_path
from . import consumers

# WebSocket URL patterns
# these are different from regular URL patterns
# they use 'ws://' instead of 'http://'
websocket_urlpatterns = [
    # chat room URL - the room_name is captured and passed to the consumer
    re_path(r'ws/chat/(?P<room_name>[\w-]+)/$', consumers.ChatConsumer.as_asgi()),
    # notifications URL - each user gets their own notification channel
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
