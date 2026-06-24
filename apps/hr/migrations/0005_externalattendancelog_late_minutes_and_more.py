# Generated for date-based external attendance operations.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0004_alter_externalattendancelog_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalattendancelog',
            name='late_minutes',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='externalattendancelog',
            name='status',
            field=models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('leave', 'Leave'), ('half_day', 'Half Day'), ('wfh', 'WFH'), ('holiday', 'Holiday'), ('weekend', 'Weekend')], default='present', max_length=20),
        ),
    ]
