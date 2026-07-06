from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel
from apps.students.models import StudentAdmission
from apps.academics.models import AcademicSession


class Result(SoftDeleteModel):
    student = models.ForeignKey(
        StudentAdmission,
        on_delete=models.CASCADE,
        related_name='results'
    )
    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name='results'
    )
    course_duration = models.CharField(max_length=100)  # Stores selected semester/year/stage
    issue_date = models.DateField()
    result_type = models.CharField(max_length=50, default='Semester')
    total_max_marks = models.IntegerField(default=0)
    total_obtained_marks = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    status_pass_fail = models.CharField(max_length=20, default='Pass')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_results'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'results_result'
        unique_together = ('student', 'session', 'course_duration')

    def __str__(self):
        return f"{self.student.student_name} - {self.course_duration}"


class ResultMarks(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name='marks')
    subject = models.ForeignKey('subjects.Subject', on_delete=models.CASCADE)
    obtained_theory_marks = models.IntegerField(null=True, blank=True)
    obtained_practical_marks = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'results_resultmarks'
        unique_together = ('result', 'subject')

    def __str__(self):
        return f"{self.result} - {self.subject.name}"

