from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0015_candidate_source_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='source',
            field=models.CharField(blank=True, max_length=160),
        ),
    ]
