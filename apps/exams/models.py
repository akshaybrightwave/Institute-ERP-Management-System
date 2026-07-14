from django.db import models
from django.conf import settings
from apps.soft_delete import SoftDeleteModel


class Exam(SoftDeleteModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField(null=True, blank=True)
    total_marks = models.IntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(default=20)

    center = models.ForeignKey('centers.Center', on_delete=models.SET_NULL, null=True, blank=True, related_name='exams_list')
    course = models.ForeignKey('courses.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='exams_list')
    course_duration = models.CharField(max_length=100, null=True, blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)

    is_published = models.BooleanField(default=False)

    pass_percentage = models.PositiveIntegerField(default=40, help_text="Minimum % required to pass this exam")
    negative_marks = models.FloatField(default=0, help_text="Marks deducted for each wrong answer (0 = disabled)")
    end_date = models.DateTimeField(null=True, blank=True, help_text="Last date/time students can attempt this exam (leave blank for no deadline)")
    allow_retake = models.BooleanField(default=False, help_text="Allow students to reattempt this exam")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='exams'
    )
    batches = models.ManyToManyField(
        'batches.Batch',
        blank=True,
        related_name='exams'
    )

    def __str__(self):
        return self.title

    @property
    def timer_label(self):
        if not self.duration_minutes:
            return ''
        if self.duration_minutes % 60 == 0:
            hours = self.duration_minutes // 60
            return f"{hours} hour" if hours == 1 else f"{hours} hours"
        return f"{self.duration_minutes} Minutes"


class Question(SoftDeleteModel):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_text = models.TextField()
    marks = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.question_text


class Option(SoftDeleteModel):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options'
    )
    text = models.CharField(max_length=255)
    # The teacher simply checks a box if this option is the right answer
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class StudentExamAttempt(SoftDeleteModel):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exam_attempts')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='attempts')

    start_time = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(auto_now=True)
    score = models.FloatField(default=0.0)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} - {self.exam.title}"


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(StudentExamAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Answer to {self.question.id} by {self.attempt.student.username}"


class ExamSchedule(SoftDeleteModel):
    center = models.ForeignKey('centers.Center', on_delete=models.CASCADE, related_name='exam_schedules_center')
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE, related_name='exam_schedules')
    duration = models.CharField(max_length=100)
    exam_center = models.ForeignKey('centers.Center', on_delete=models.CASCADE, related_name='exam_schedules_exam_center')
    session = models.ForeignKey('academics.AcademicSession', on_delete=models.CASCADE, related_name='exam_schedules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.course.name} - {self.session.session_name}"

    # NOTE: StudentProfile and TeacherProfile have been moved to:
    #   apps/students/models.py  →  StudentProfile
    #   apps/teachers/models.py  →  TeacherProfile


class ExamStudentAssignment(SoftDeleteModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='student_assignments')
    student = models.ForeignKey('students.StudentAdmission', on_delete=models.CASCADE, related_name='exam_assignments')
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    assigned_date = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"{self.exam.title} - {self.student.student_name}"


# ---------------------------------------------------------------------------
# Exam Centre — Independent master module (NOT related to Center Information)
# ---------------------------------------------------------------------------

class ExamCentre(SoftDeleteModel):
    """
    A dedicated Exam Centre is a physical examination location.
    This model is completely independent from the Center Information module
    (apps.centers.Center). Do NOT merge or link these two models.
    """
    centre_name = models.CharField(max_length=255, verbose_name="Centre Name")
    centre_code = models.CharField(max_length=50, unique=True, verbose_name="Centre Code")
    address = models.TextField(verbose_name="Address")
    is_active = models.BooleanField(default=True, verbose_name="Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-id']
        verbose_name = "Exam Centre"
        verbose_name_plural = "Exam Centres"

    def __str__(self):
        return f"{self.centre_name} ({self.centre_code})"
