# Generated manually for the Investigator Panel Phase 1 role setup.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_alter_user_role'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('SUPER_ADMIN', 'Super Admin'),
                    ('admin', 'Admin'),
                    ('superadmin', 'Super Admin'),
                    ('center', 'Center'),
                    ('teacher', 'Teacher'),
                    ('student', 'Student'),
                    ('hr', 'HR'),
                    ('telecaller', 'Telecaller'),
                    ('counselor', 'Counselor'),
                    ('investigator', 'Investigator'),
                ],
                max_length=20,
            ),
        ),
    ]
