from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel


class StudentProfile(SoftDeleteModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    email = models.EmailField()
    profile_picture = models.ImageField(upload_to='student_profiles/', blank=True, null=True)
    bio = models.TextField(blank=True)
    batch = models.ForeignKey(
        'batches.Batch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        # Pin to the existing DB table so no ALTER TABLE is needed.
        # The table was originally created by the 'exam' app as exam_studentprofile.
        db_table = 'exam_studentprofile'

    def __str__(self):
        return self.full_name
