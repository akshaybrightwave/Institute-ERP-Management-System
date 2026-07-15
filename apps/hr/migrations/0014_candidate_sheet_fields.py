from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0013_unify_assignment_status_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='candidate',
            name='interview_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='candidate',
            name='notice_period',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='candidate',
            name='location',
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='candidate',
            name='remarks',
            field=models.TextField(blank=True),
        ),
    ]
