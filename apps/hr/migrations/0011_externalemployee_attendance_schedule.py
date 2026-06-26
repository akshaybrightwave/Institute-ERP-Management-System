# Generated for employee-specific attendance timing.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0010_remove_candidate_certificates_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalemployee',
            name='scheduled_login_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='externalemployee',
            name='scheduled_logout_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]
