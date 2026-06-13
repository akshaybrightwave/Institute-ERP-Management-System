from django.db import models
from django.conf import settings


class TeacherProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField()
    profile_picture = models.ImageField(upload_to='teacher_profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    class Meta:
        # Pin to the existing DB table so no ALTER TABLE is needed.
        # The table was originally created by the 'exam' app as exam_teacherprofile.
        db_table = 'exam_teacherprofile'

    def __str__(self):
        return self.full_name
