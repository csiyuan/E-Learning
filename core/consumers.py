import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, CustomUser

# Handles websocket connections for chat
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        self.user = self.scope['user']

        # join group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # when someone leaves the chat
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # this runs when we receive a message from the websocket
    async def receive(self, text_data):
        # parse the JSON data from the client
        data = json.loads(text_data)
        message_content = data['message']
        username = data['username']
        
        # save message to database
        full_name, timestamp = await self.save_message(username, self.room_name, message_content)
        
        # broadcast the message to everyone in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'username': username,
                'full_name': full_name,
                'timestamp': timestamp
            }
        )
    
    # this is called when the group receives a message
    # the 'type' above maps to this function name
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        timestamp = event.get('timestamp')
        
        # send the message to the websocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'full_name': event.get('full_name', username),
            'timestamp': timestamp
        }))
    
    # save message to database
    # using database_sync_to_async decorator for ORM operations
    @database_sync_to_async
    def save_message(self, username, room, message):
        # get the user object
        try:
            from django.utils import timezone
            user = CustomUser.objects.get(username=username)
            # create the message
            chat_msg = ChatMessage.objects.create(
                sender=user,
                room_name=room,
                content=message
            )
            return user.get_full_name() or user.username, chat_msg.created_at.isoformat()
        except CustomUser.DoesNotExist:
            from django.utils import timezone
            # shouldn't happen but just in case
            return username, timezone.now().isoformat()


# notification consumer - sends real-time alerts to users
# struggled with this at first but finally got it working
class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # each user has their own notification channel
        self.user = self.scope['user']
        
        # auth check 
        if self.user.is_anonymous:
            await self.close()
            return
        
        self.notification_group = f'notifications_{self.user.username}'
        
        # join the group
        await self.channel_layer.group_add(
            self.notification_group,
            self.channel_name
        )
        
        await self.accept()
        # print("notify socket connected")
    
    async def disconnect(self, close_code):
        # leave notification group when disconnecting
        if hasattr(self, 'notification_group'):
            await self.channel_layer.group_discard(
                self.notification_group,
                self.channel_name
            )
    
    # this gets called when a notification is sent to the user
    async def send_notification(self, event):
        notification_type = event['notification_type']
        message = event['message']
        
        # send notification to websocket
        await self.send(text_data=json.dumps({
            'type': notification_type,
            'message': message
        }))

