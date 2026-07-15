from django.db import migrations, models


CALL_STATUS_CHOICES = [
    ('NEW', 'New'),
    ('ACCEPTED', 'Accepted'),
    ('BUSY', 'Busy'),
    ('NO_ANSWER', 'Ringing'),
    ('CALL_BACK', 'Call Back'),
    ('CALL_DISCONNECTED', 'Call Disconnected'),
    ('WRONG_NUMBER', 'Wrong Number'),
    ('INVALID_NUMBER', 'Invalid Number'),
    ('INTERESTED', 'Interested'),
    ('NOT_INTERESTED', 'Not Interested'),
    ('CALL_CONNECTED', 'Call Connected'),
    ('SWITCHED_OFF', 'Switched Off'),
    ('PENDING_FOLLOW_UP', 'Pending Follow Up'),
    ('OTHER', 'Other'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0024_inquirycallstatushistory'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inquiry',
            name='call_status',
            field=models.CharField(
                choices=CALL_STATUS_CHOICES,
                db_index=True,
                default='NEW',
                max_length=25,
            ),
        ),
        migrations.AlterField(
            model_name='inquirycallstatushistory',
            name='call_status',
            field=models.CharField(
                choices=CALL_STATUS_CHOICES,
                db_index=True,
                max_length=25,
            ),
        ),
    ]
