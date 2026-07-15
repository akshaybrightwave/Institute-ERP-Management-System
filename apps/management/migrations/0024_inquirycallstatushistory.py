from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0023_alter_inquiry_call_status'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InquiryCallStatusHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('call_status', models.CharField(choices=[('NEW', 'New'), ('ACCEPTED', 'Accepted'), ('BUSY', 'Busy'), ('NO_ANSWER', 'Ringing'), ('CALL_BACK', 'Call Back'), ('CALL_DISCONNECTED', 'Call Disconnected'), ('WRONG_NUMBER', 'Wrong Number'), ('INTERESTED', 'Interested'), ('SWITCHED_OFF', 'Switched Off'), ('PENDING_FOLLOW_UP', 'Pending Follow Up'), ('OTHER', 'Other')], db_index=True, max_length=25)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('inquiry', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='call_status_history', to='management.inquiry')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inquiry_call_status_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='inquirycallstatushistory',
            index=models.Index(fields=['inquiry', '-created_at'], name='mg_inq_call_hist_idx'),
        ),
        migrations.AddIndex(
            model_name='inquirycallstatushistory',
            index=models.Index(fields=['call_status', '-created_at'], name='mg_inq_call_status_idx'),
        ),
    ]
