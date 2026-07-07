import os
import uuid
from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel
from apps.centers.models import Center
from apps.courses.models import Course
from apps.subjects.models import Subject


def study_material_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    # Get filename without path and extension
    base = os.path.basename(filename)
    name = os.path.splitext(base)[0]
    unique_id = uuid.uuid4().hex[:8]
    new_filename = f"{name}_{unique_id}.{ext}"
    return os.path.join('study_materials', new_filename)


class StudyMaterial(SoftDeleteModel):
    FILE_TYPE_CHOICES = [
        ('PDF', 'PDF'),
        ('DOC', 'DOC'),
        ('PPT', 'PPT'),
        ('Excel', 'Excel'),
        ('ZIP', 'ZIP'),
        ('Image', 'Image'),
        ('Video Link', 'Video Link'),
    ]

    center = models.ForeignKey(Center, on_delete=models.CASCADE, related_name='study_materials')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='study_materials')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file_type = models.CharField(max_length=50, choices=FILE_TYPE_CHOICES)
    upload_file = models.FileField(upload_to=study_material_upload_path, blank=True, null=True)
    external_url = models.URLField(blank=True, null=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='uploaded_materials')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'exam_studymaterial'
        unique_together = ('center', 'course', 'title')

    def __str__(self):
        return f"{self.title} ({self.course.name})"
