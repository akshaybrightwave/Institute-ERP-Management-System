from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0025_alter_inquiry_call_status_group_choices'),
    ]

    operations = [
        migrations.AddField(
            model_name='inquiry',
            name='college_name',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]
