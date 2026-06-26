import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Lead

class LeadRemarkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lead_id = self.scope['url_route']['kwargs']['lead_id']
        self.room_group_name = f'lead_remarks_{self.lead_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        has_access = await self.check_lead_access(self.lead_id, self.user)
        if not has_access:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Broadcasts are triggered via HTTP views, so no client-to-server messaging required.
        pass

    async def remark_message(self, event):
        payload = event['payload']
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def check_lead_access(self, lead_id, user):
        try:
            lead = Lead.objects.get(pk=lead_id)
            if user.role in ('admin', 'superadmin'):
                return True
            if user.role == 'telecaller' and lead.assigned_telecaller == user:
                return True
            if user.role == 'counselor' and lead.assigned_counselor == user:
                return True
            return False
        except Lead.DoesNotExist:
            return False
