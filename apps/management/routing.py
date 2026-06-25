from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/lead/(?P<lead_id>\w+)/remarks/$', consumers.LeadRemarkConsumer.as_asgi()),
]
