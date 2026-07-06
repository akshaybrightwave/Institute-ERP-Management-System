from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel
from apps.students.models import StudentAdmission
from apps.academics.models import AcademicSession
from apps.courses.models import Course
from apps.centers.models import Center


class Certificate(SoftDeleteModel):
    student = models.ForeignKey(
        StudentAdmission,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        related_name='certificates',
        null=True,
        blank=True
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='certificates',
        null=True,
        blank=True
    )
    course_duration = models.CharField(max_length=100, null=True, blank=True)
    certificate_number = models.CharField(max_length=100, unique=True)
    issue_date = models.DateField()
    examination_conducted_date = models.DateField(null=True, blank=True)
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_certificates'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'certificates_certificate'
        unique_together = ('student', 'session', 'course_duration')

    def __str__(self):
        return f"{self.certificate_number} - {self.student.student_name}"
