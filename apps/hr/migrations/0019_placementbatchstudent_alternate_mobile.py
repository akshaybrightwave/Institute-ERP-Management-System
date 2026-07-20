from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0018_emailconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='placementbatchstudent',
            name='alternate_mobile',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
