import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Connect to notification channel
        """
        if not self.scope['user'].is_authenticated or not self.scope['user'].is_superuser:
            # Disconnect if user is not authenticated or not superuser
            await self.close()
            return

        # Join managers group
        await self.channel_layer.group_add(
            "restaurant_managers",
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        """
        Disconnect from channel
        """
        await self.channel_layer.group_discard(
            "restaurant_managers",
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from client
        """
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to group
        await self.channel_layer.group_send(
            "restaurant_managers",
            {
                'type': 'notification_message',
                'message': message
            }
        )

    async def notification_message(self, event):
        """
        Send notification to client
        """
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        })) 