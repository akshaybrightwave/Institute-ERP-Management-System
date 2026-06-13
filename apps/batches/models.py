from django.db import models
from apps.courses.models import Course
from apps.teachers.models import TeacherProfile


class Batch(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name
