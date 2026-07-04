from django.db import models
from apps.soft_delete import SoftDeleteModel
from apps.courses.models import Course


class Subject(SoftDeleteModel):
    SUBJECT_TYPE_CHOICES = [
        ('Theory', 'Theory'),
        ('Practical', 'Practical'),
        ('Both', 'Both'),
    ]

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subjects'
    )
    duration_offset = models.CharField(max_length=100)
    subject_code = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    subject_type = models.CharField(
        max_length=20,
        choices=SUBJECT_TYPE_CHOICES,
        default='Theory'
    )
    theory_max_marks = models.IntegerField(default=100, null=True, blank=True)
    theory_min_marks = models.IntegerField(null=True, blank=True)
    practical_max_marks = models.IntegerField(default=100, null=True, blank=True)
    practical_min_marks = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.subject_code})"


class SubjectOrder(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subject_orders')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_orders')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('course', 'subject')

    def __str__(self):
        return f"{self.course.name} - {self.subject.name} (Order: {self.order})"
