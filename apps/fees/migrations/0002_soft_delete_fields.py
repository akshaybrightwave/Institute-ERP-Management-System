from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fees', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='feepayment',
            name='deleted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='feepayment',
            name='is_deleted',
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
