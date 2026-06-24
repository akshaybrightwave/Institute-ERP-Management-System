from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exam', '0004_exam_batches'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='exam',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='option',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='option',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='question',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='question',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='studentexamattempt',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='studentexamattempt',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
