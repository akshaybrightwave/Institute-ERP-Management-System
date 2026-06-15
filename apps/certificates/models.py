from django.db import models
from apps.students.models import StudentProfile
from apps.batches.models import Batch
from apps.courses.models import Course


class Certificate(models.Model):
    STATUS_CHOICES = [
        ('issued', 'Issued'),
        ('revoked', 'Revoked'),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    certificate_number = models.CharField(
        max_length=100,
        unique=True
    )
    issue_date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='issued'
    )
    remarks = models.TextField(
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.certificate_number} - {self.student.full_name}"
