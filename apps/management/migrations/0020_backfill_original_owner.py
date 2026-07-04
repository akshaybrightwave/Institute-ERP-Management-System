from django.db import migrations


def backfill_original_owner(apps, schema_editor):
    Lead = apps.get_model('management', 'Lead')

    for lead in Lead.objects.all().iterator():
        updates = []

        if lead.assigned_telecaller_id and not lead.first_assigned_telecaller_id:
            lead.first_assigned_telecaller_id = lead.assigned_telecaller_id
            updates.append('first_assigned_telecaller')

        if lead.assigned_counselor_id and not lead.first_assigned_counselor_id:
            lead.first_assigned_counselor_id = lead.assigned_counselor_id
            updates.append('first_assigned_counselor')

        if not lead.first_assigned_user_id:
            telecaller_date = lead.telecaller_assigned_at or lead.assigned_at
            counselor_date = lead.counselor_assigned_at or lead.assigned_at

            if lead.first_assigned_telecaller_id and lead.first_assigned_counselor_id:
                if telecaller_date and counselor_date:
                    telecaller_was_first = telecaller_date <= counselor_date
                else:
                    telecaller_was_first = bool(telecaller_date or not counselor_date)
                lead.first_assigned_user_id = (
                    lead.first_assigned_telecaller_id
                    if telecaller_was_first
                    else lead.first_assigned_counselor_id
                )
                lead.first_assigned_date = telecaller_date if telecaller_was_first else counselor_date
            elif lead.first_assigned_telecaller_id:
                lead.first_assigned_user_id = lead.first_assigned_telecaller_id
                lead.first_assigned_date = telecaller_date
            elif lead.first_assigned_counselor_id:
                lead.first_assigned_user_id = lead.first_assigned_counselor_id
                lead.first_assigned_date = counselor_date

            if lead.first_assigned_user_id:
                updates.append('first_assigned_user')
                if lead.first_assigned_date:
                    updates.append('first_assigned_date')

        if updates:
            lead.save(update_fields=sorted(set(updates)))


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0019_lead_first_assigned_date_lead_first_assigned_user'),
    ]

    operations = [
        migrations.RunPython(backfill_original_owner, migrations.RunPython.noop),
    ]
