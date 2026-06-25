import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Lead

class LeadRemarkConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lead_id = self.scope['url_route']['kwargs']['lead_id']
        self.room_group_name = f'lead_remarks_{self.lead_id}'
        self.user = self.scope['user']
        print(f"WS CONNECTING: User={self.user}, Lead={self.lead_id}")

        if not self.user.is_authenticated:
            print("WS REJECTED: Unauthenticated")
            await self.close()
            return

        has_access = await self.check_lead_access(self.lead_id, self.user)
        if not has_access:
            print(f"WS REJECTED: Access denied for {self.user} on lead {self.lead_id}")
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        print("WS CLIENT CONNECTED", self.room_group_name)
        print("WS CONNECTED", self.scope["user"])
        print("GROUP JOINED", self.room_group_name)

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
        print("BROADCAST RECEIVED", event)
        print(f"WS RECEIVING BROADCAST: Sending payload to {self.user}")
        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def check_lead_access(self, lead_id, user):
        try:
            lead = Lead.objects.get(pk=lead_id)
            if user.role == 'admin':
                return True
            if user.role == 'telecaller' and lead.assigned_telecaller == user:
                return True
            if user.role == 'counselor' and lead.assigned_counselor == user:
                return True
            return False
        except Lead.DoesNotExist:
            return False
