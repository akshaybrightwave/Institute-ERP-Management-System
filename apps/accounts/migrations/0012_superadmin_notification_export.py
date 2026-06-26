# Generated manually for isolated Super Admin notification and export centers.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_authactivitylog_super_admin'),
    ]

    operations = [
        migrations.CreateModel(
            name='SuperAdminNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160)),
                ('message', models.TextField(blank=True)),
                ('notification_type', models.CharField(choices=[('USER_CREATED', 'New User Created'), ('PASSWORD_RESET', 'Password Reset'), ('FOLLOWUP_OVERDUE', 'Follow-up Overdue'), ('EXPORT_COMPLETED', 'Export Completed'), ('SYSTEM_ALERT', 'System Alert')], db_index=True, default='SYSTEM_ALERT', max_length=30)),
                ('is_read', models.BooleanField(db_index=True, default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_superadmin_notifications', to='accounts.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SuperAdminExport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('report_name', models.CharField(max_length=120)),
                ('export_format', models.CharField(choices=[('csv', 'CSV'), ('excel', 'Excel'), ('pdf', 'PDF')], max_length=20)),
                ('status', models.CharField(choices=[('completed', 'Completed'), ('failed', 'Failed'), ('pending', 'Pending')], db_index=True, default='completed', max_length=20)),
                ('file_name', models.CharField(blank=True, max_length=180)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('requested_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='superadmin_exports', to='accounts.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
