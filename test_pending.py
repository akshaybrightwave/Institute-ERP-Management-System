import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'institute_erp.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from apps.management.models import Lead, User

counselor = User.objects.get(email='counselor@1234')
leads = Lead.objects.filter(assigned_counselor=counselor, converted_at__isnull=False)

followup_overdue_threshold = timezone.now() - timedelta(hours=24)
leads_filtered = leads.filter(counselor_status='FOLLOW_UP_REQUIRED')

pending = leads_filtered.filter(counselor_status_updated_at__gte=followup_overdue_threshold)
overdue = leads_filtered.filter(counselor_status_updated_at__lt=followup_overdue_threshold)

print(f"Total leads: {leads.count()}")
print(f"Pending: {pending.count()}")
print(f"Overdue: {overdue.count()}")

