from django.apps import AppConfig


class ExamsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.exams'
    # IMPORTANT: Keep label='exam' so all existing migrations and DB table
    # names (exam_exam, exam_question, etc.) continue to work unchanged.
    label = 'exam'
