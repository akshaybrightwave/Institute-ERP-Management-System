from django.contrib import admin
from apps.exams.models import Exam, Question, Option, StudentExamAttempt, StudentAnswer

# Exam-domain models only.
# StudentProfile is registered in apps/students/admin.py
# TeacherProfile is registered in apps/teachers/admin.py

admin.site.register(Exam)
admin.site.register(Question)
admin.site.register(Option)
admin.site.register(StudentExamAttempt)
admin.site.register(StudentAnswer)
