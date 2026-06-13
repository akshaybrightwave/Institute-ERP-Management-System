"""
Migration 0003: Transfer StudentProfile and TeacherProfile ownership to their
dedicated apps (apps.students and apps.teachers) without touching the database.

Strategy: SeparateDatabaseAndState
  - state_operations: Remove StudentProfile and TeacherProfile from the 'exam'
    app's Django state (so Django no longer considers them owned by this app).
  - database_operations: Empty — tables exam_studentprofile and exam_teacherprofile
    are NOT touched. The new apps (students, teachers) will claim ownership via
    their own migrations, pinning db_table to the existing table names.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exam', '0002_exam_allow_retake_exam_end_date_exam_negative_marks_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='StudentProfile'),
                migrations.DeleteModel(name='TeacherProfile'),
            ],
            database_operations=[
                # Intentionally empty — tables remain intact.
                # apps/students and apps/teachers will manage them going forward.
            ]
        )
    ]
