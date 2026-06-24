# Generated for project module operations.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0005_externalattendancelog_late_minutes_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectCompany',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=180)),
                ('industry', models.CharField(blank=True, max_length=140)),
                ('contact_person', models.CharField(blank=True, max_length=140)),
                ('designation', models.CharField(blank=True, max_length=140)),
                ('mobile', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('website', models.URLField(blank=True)),
                ('address', models.TextField(blank=True)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('project_value', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('logo', models.ImageField(blank=True, upload_to='hr/projects/companies/')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_companies', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectDrive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('project_name', models.CharField(blank=True, max_length=180)),
                ('role_required', models.CharField(blank=True, max_length=160)),
                ('drive_date', models.DateField(blank=True, null=True)),
                ('project_value', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('eligibility_criteria', models.TextField(blank=True)),
                ('venue', models.CharField(blank=True, max_length=220)),
                ('remarks', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('upcoming', 'Upcoming'), ('scheduled', 'Scheduled'), ('active', 'Active'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='upcoming', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='drives', to='hr.projectcompany')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_drives', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['drive_date', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('company', 'Company Added'), ('drive', 'Project Drive Created'), ('assignment', 'Employees Assigned'), ('interview', 'Interview Scheduled'), ('allocation', 'Allocation Updated'), ('result', 'Result Published')], max_length=20)),
                ('title', models.CharField(max_length=180)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='hr.projectcompany')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('drive', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='activities', to='hr.projectdrive')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectEmployeeAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('employee_name', models.CharField(blank=True, max_length=160)),
                ('employee_code', models.CharField(blank=True, max_length=30)),
                ('department', models.CharField(blank=True, max_length=120)),
                ('designation', models.CharField(blank=True, max_length=140)),
                ('skills', models.TextField(blank=True)),
                ('interview_status', models.CharField(choices=[('scheduled', 'Scheduled'), ('appeared', 'Appeared'), ('absent', 'Absent'), ('selected', 'Selected'), ('rejected', 'Rejected')], default='scheduled', max_length=20)),
                ('final_status', models.CharField(choices=[('pending', 'Pending'), ('selected', 'Selected'), ('rejected', 'Rejected'), ('allocated', 'Allocated'), ('released', 'Released')], default='pending', max_length=20)),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assigned_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_assignments_created', to=settings.AUTH_USER_MODEL)),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='project_assignments', to='hr.projectcompany')),
                ('drive', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assignments', to='hr.projectdrive')),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_assignments', to='hr.externalemployee')),
            ],
            options={
                'ordering': ['-assigned_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectAllocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('billing_rate', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('allocation_status', models.CharField(choices=[('allocated', 'Allocated'), ('not_allocated', 'Not Allocated'), ('awaiting', 'Awaiting Allocation'), ('released', 'Released')], default='awaiting', max_length=20)),
                ('allocation_date', models.DateField(blank=True, null=True)),
                ('release_date', models.DateField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assignment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='allocation', to='hr.projectemployeeassignment')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='allocations', to='hr.projectcompany')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_allocations_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='ProjectInterview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interview_round', models.CharField(blank=True, max_length=140)),
                ('date', models.DateField(blank=True, null=True)),
                ('time', models.TimeField(blank=True, null=True)),
                ('venue', models.CharField(blank=True, max_length=220)),
                ('interviewer', models.CharField(blank=True, max_length=160)),
                ('remarks', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('scheduled', 'Scheduled'), ('appeared', 'Appeared'), ('absent', 'Absent'), ('selected', 'Selected'), ('rejected', 'Rejected')], default='scheduled', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('assignment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='interviews', to='hr.projectemployeeassignment')),
                ('company', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_interviews', to='hr.projectcompany')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_interviews_created', to=settings.AUTH_USER_MODEL)),
                ('drive', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='project_interviews', to='hr.projectdrive')),
            ],
            options={
                'ordering': ['date', 'time', '-updated_at'],
            },
        ),
    ]
