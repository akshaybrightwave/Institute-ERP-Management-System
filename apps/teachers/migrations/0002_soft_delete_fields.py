from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='teacherprofile',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
