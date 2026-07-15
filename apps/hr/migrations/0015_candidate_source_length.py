from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0014_candidate_sheet_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candidate',
            name='source',
            field=models.CharField(blank=True, choices=[('naukri', 'Naukri.com'), ('linkedin', 'LinkedIn'), ('referral', 'Referral'), ('walk_in', 'Walk-in'), ('website', 'Website'), ('campus', 'Campus'), ('other', 'Other')], max_length=160),
        ),
    ]
