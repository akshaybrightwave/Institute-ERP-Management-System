# Generated for external HR quick attendance statuses.

from django.db import migrations, models


def map_late_to_half_day(apps, schema_editor):
    ExternalAttendanceLog = apps.get_model('hr', 'ExternalAttendanceLog')
    ExternalAttendanceLog.objects.filter(status='late').update(status='half_day')


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0003_externalemployee_externalattendancelog'),
    ]

    operations = [
        migrations.RunPython(map_late_to_half_day, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='externalattendancelog',
            name='status',
            field=models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave'), ('half_day', 'Half Day')], default='present', max_length=20),
        ),
    ]
