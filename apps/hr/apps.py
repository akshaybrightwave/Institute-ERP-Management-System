from django.apps import AppConfig


class HrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hr'

    def ready(self):
        from . import attendance_automation  # noqa: F401
