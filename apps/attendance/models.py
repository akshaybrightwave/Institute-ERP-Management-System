from django.db import models
from apps.batches.models import Batch
from apps.students.models import StudentProfile
from apps.teachers.models import TeacherProfile


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES
    )
    marked_by = models.ForeignKey(
        TeacherProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='marked_attendances'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.status}"
