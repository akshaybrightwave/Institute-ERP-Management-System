# Generated to align manually-created AuthActivityLog index names with Django's autodetector.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_superadmin_notification_export'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='authactivitylog',
            new_name='accounts_au_event_t_15c7a8_idx',
            old_name='accounts_au_event__729626_idx',
        ),
        migrations.RenameIndex(
            model_name='authactivitylog',
            new_name='accounts_au_usernam_fa2cd7_idx',
            old_name='accounts_au_usernam_16c1de_idx',
        ),
    ]
