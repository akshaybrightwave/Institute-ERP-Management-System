from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('batches', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='batch',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
