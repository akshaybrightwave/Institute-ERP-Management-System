from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0002_studentprofile_batch'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='studentprofile',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
