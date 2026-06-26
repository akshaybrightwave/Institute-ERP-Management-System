import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam_portal.settings')
django.setup()

from apps.management.models import Lead

leads_to_update = []
for lead in Lead.objects.all():
    changed = False
    if lead.priority == 'Low':
        lead.priority = 'Cold'
        changed = True
    elif lead.priority == 'Medium':
        lead.priority = 'Warm'
        changed = True
    elif lead.priority == 'High':
        lead.priority = 'Hot'
        changed = True
    
    if changed:
        leads_to_update.append(lead)

if leads_to_update:
    Lead.objects.bulk_update(leads_to_update, ['priority'])
    print(f"Updated {len(leads_to_update)} leads.")
else:
    print("No leads needed updating.")
