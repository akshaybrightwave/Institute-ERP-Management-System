from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel
from apps.students.models import StudentAdmission
from apps.academics.models import AcademicSession


class AdmitCard(SoftDeleteModel):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Published', 'Published'),
    ]

    student = models.ForeignKey(
        StudentAdmission,
        on_delete=models.CASCADE,
        related_name='admit_cards'
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='admit_cards'
    )
    roll_number = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Published')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_admit_cards'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admit_card_admitcard'
        unique_together = ('student', 'session')

    def __str__(self):
        return f"{self.student.student_name} - {self.roll_number}"

