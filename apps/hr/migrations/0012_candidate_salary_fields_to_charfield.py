# Generated for candidate salary text input support.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0011_externalemployee_attendance_schedule'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='experience',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='current_salary',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='candidate',
            name='expected_salary',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
