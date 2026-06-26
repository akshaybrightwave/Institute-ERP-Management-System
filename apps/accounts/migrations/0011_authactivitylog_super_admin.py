# Generated manually for Super Admin bootstrap and authentication activity logs.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('SUPER_ADMIN', 'Super Admin'), ('admin', 'Admin'), ('center', 'Center'), ('teacher', 'Teacher'), ('student', 'Student'), ('hr', 'HR'), ('telecaller', 'Telecaller'), ('counselor', 'Counselor')], max_length=20),
        ),
        migrations.CreateModel(
            name='AuthActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(blank=True, max_length=150)),
                ('event_type', models.CharField(choices=[('BOOTSTRAP_SUPER_ADMIN', 'Bootstrap Super Admin'), ('LOGIN_SUCCESS', 'Login Success'), ('LOGIN_FAILED', 'Login Failed'), ('LOGOUT', 'Logout'), ('REGISTRATION_BLOCKED', 'Registration Blocked'), ('USER_CREATED', 'User Created'), ('PASSWORD_RESET', 'Password Reset'), ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'), ('SESSION_INVALID', 'Session Invalid')], db_index=True, max_length=40)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255)),
                ('path', models.CharField(blank=True, max_length=255)),
                ('details', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='auth_activity_logs', to='accounts.user')),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['event_type', '-created_at'], name='accounts_au_event__729626_idx'),
                    models.Index(fields=['username', '-created_at'], name='accounts_au_usernam_16c1de_idx'),
                ],
            },
        ),
    ]
