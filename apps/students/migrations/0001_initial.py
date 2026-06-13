"""
Migration 0001: Claim ownership of StudentProfile for the 'students' app.

Strategy: SeparateDatabaseAndState
  - state_operations: Create StudentProfile in Django's ORM state for the
    'students' app, with db_table pinned to 'exam_studentprofile'.
  - database_operations: Empty — table already exists; no CREATE TABLE needed.

This depends on exam migration 0003 which removed StudentProfile from the
'exam' app's state, so there is no duplicate ownership conflict.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        # Must run after the 'exam' app removes StudentProfile from its state
        ('exam', '0003_transfer_profiles_to_dedicated_apps'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='StudentProfile',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('full_name', models.CharField(max_length=100)),
                        ('phone', models.CharField(blank=True, max_length=15)),
                        ('email', models.EmailField(max_length=254)),
                        ('profile_picture', models.ImageField(blank=True, null=True, upload_to='student_profiles/')),
                        ('bio', models.TextField(blank=True)),
                        ('user', models.OneToOneField(
                            on_delete=django.db.models.deletion.CASCADE,
                            to=settings.AUTH_USER_MODEL
                        )),
                    ],
                    options={
                        'db_table': 'exam_studentprofile',
                    },
                ),
            ],
            database_operations=[
                # Intentionally empty — exam_studentprofile table already exists.
            ]
        )
    ]
