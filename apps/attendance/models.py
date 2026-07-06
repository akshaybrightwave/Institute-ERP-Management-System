from django.db import models
from apps.batches.models import Batch
from apps.students.models import StudentProfile
from apps.teachers.models import TeacherProfile


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
        ('holiday', 'Holiday'),
        ('half_day', 'Half Day'),
    ]

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name='attendances',
        null=True, blank=True
    )
    timetable_name = models.CharField(max_length=255, null=True, blank=True)
    student = models.ForeignKey(
        'students.StudentAdmission',
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='present'
    )
    remark = models.CharField(max_length=255, blank=True, default='')
    marked_by = models.ForeignKey(
        TeacherProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='marked_attendances'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'timetable_name', 'date')

    def __str__(self):
        return f"{self.student.student_name} - {self.date} - {self.status}"
