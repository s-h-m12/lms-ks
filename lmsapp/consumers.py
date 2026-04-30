import json
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from .models import ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'text')

        # Получаем пользователя прямо из сессии Channels
        user = self.scope['user']
        if not user.is_authenticated:
            return

        if message_type == 'text':
            message = data.get('message', '')
            await self.save_text_message(user, self.room_name, message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'text',
                    'message': message,
                    'username': user.username,
                }
            )

        elif message_type == 'image':
            image_data = data.get('image_data')
            image_url = await self.save_image_message(user, self.room_name, image_data)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'image',
                    'image_url': image_url,
                    'username': user.username,
                }
            )

        elif message_type == 'file':
            file_data = data.get('file_data')
            filename = data.get('filename')
            file_url = await self.save_file_message(user, self.room_name, file_data, filename)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_type': 'file',
                    'file_url': file_url,
                    'filename': filename,
                    'username': user.username,
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_text_message(self, user, room_name, message):
        return ChatMessage.objects.create(
            user=user,
            room=room_name,
            message=message
        )

    @database_sync_to_async
    def save_image_message(self, user, room_name, image_data):
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        image_file = ContentFile(base64.b64decode(imgstr), name=f'image_{user.id}_{room_name}.{ext}')
        msg = ChatMessage.objects.create(
            user=user,
            room=room_name,
            image=image_file
        )
        return msg.image.url

    @database_sync_to_async
    def save_file_message(self, user, room_name, file_data, filename):
        format, filestr = file_data.split(';base64,')
        file_content = ContentFile(base64.b64decode(filestr), name=filename)
        msg = ChatMessage.objects.create(
            user=user,
            room=room_name,
            file=file_content
        )
        return msg.file.url
