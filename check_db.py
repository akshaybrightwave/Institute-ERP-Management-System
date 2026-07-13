import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam_portal.settings')
django.setup()

from apps.batches.models import Batch
from apps.centers.models import CenterCourseAssignment

total_batches = Batch.objects.count()
batches_with_center = Batch.objects.filter(center__isnull=False).count()
orphaned_batches = Batch.objects.filter(center__isnull=True).count()

print(f"Total Batches: {total_batches}")
print(f"Batches with Center: {batches_with_center}")
print(f"Orphaned Batches (NULL center): {orphaned_batches}")

total_assignments = CenterCourseAssignment.objects.count()
active_assignments = CenterCourseAssignment.objects.filter(is_active=True).count()
print(f"Total CenterCourseAssignments: {total_assignments}")
print(f"Active Assignments: {active_assignments}")

