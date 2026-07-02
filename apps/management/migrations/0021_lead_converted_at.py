from django.db import migrations, models
from django.db.models import Q


def backfill_converted_at(apps, schema_editor):
    Lead = apps.get_model('management', 'Lead')
    LeadActivity = apps.get_model('management', 'LeadActivity')

    converted_leads = Lead.objects.filter(
        converted_at__isnull=True,
        inquiry__status='Qualified',
    )

    for lead in converted_leads.iterator():
        conversion_activity = LeadActivity.objects.filter(
            Q(activity_type='LEAD_CREATED')
            | Q(description__icontains='converted')
            | Q(description__icontains='qualified'),
            lead_id=lead.id,
        ).order_by('created_at').first()

        converted_at = (
            conversion_activity.created_at
            if conversion_activity
            else lead.created_at or lead.assigned_at
        )

        if converted_at:
            Lead.objects.filter(pk=lead.pk, converted_at__isnull=True).update(converted_at=converted_at)


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0020_backfill_original_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='lead',
            name='converted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_converted_at, migrations.RunPython.noop),
    ]
