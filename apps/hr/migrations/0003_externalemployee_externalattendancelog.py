# Generated for the external HR management module.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0002_placementcompany_placementdrive_placementactivity_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalEmployee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('branch', models.CharField(choices=[('thane', 'Dcodetech Thane'), ('nashik', 'Dcodetech Nashik')], max_length=20)),
                ('employee_id', models.CharField(max_length=30, unique=True)),
                ('full_name', models.CharField(max_length=160)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('mobile', models.CharField(blank=True, max_length=20)),
                ('photo', models.ImageField(blank=True, upload_to='hr/external/employees/')),
                ('department', models.CharField(blank=True, max_length=120)),
                ('designation', models.CharField(blank=True, max_length=140)),
                ('joining_date', models.DateField(blank=True, null=True)),
                ('employment_type', models.CharField(choices=[('full_time', 'Full Time'), ('part_time', 'Part Time'), ('contract', 'Contract'), ('intern', 'Intern')], default='full_time', max_length=20)),
                ('reporting_manager', models.CharField(blank=True, max_length=160)),
                ('status', models.CharField(choices=[('active', 'Active'), ('probation', 'Probation'), ('notice', 'Notice Period'), ('inactive', 'Inactive')], default='active', max_length=20)),
                ('dob', models.DateField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')], max_length=20)),
                ('address', models.TextField(blank=True)),
                ('emergency_contact', models.CharField(blank=True, max_length=80)),
                ('monthly_attendance', models.PositiveSmallIntegerField(default=0)),
                ('late_count', models.PositiveSmallIntegerField(default=0)),
                ('leave_balance', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('resume', models.FileField(blank=True, upload_to='hr/external/documents/resumes/')),
                ('offer_letter', models.FileField(blank=True, upload_to='hr/external/documents/offers/')),
                ('aadhaar', models.FileField(blank=True, upload_to='hr/external/documents/aadhaar/')),
                ('pan', models.FileField(blank=True, upload_to='hr/external/documents/pan/')),
                ('bank_details', models.FileField(blank=True, upload_to='hr/external/documents/bank/')),
                ('certificates', models.FileField(blank=True, upload_to='hr/external/documents/certificates/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='external_employees_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['branch', 'full_name'],
            },
        ),
        migrations.CreateModel(
            name='ExternalAttendanceLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.localdate)),
                ('check_in', models.TimeField(blank=True, null=True)),
                ('check_out', models.TimeField(blank=True, null=True)),
                ('working_hours', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('status', models.CharField(choices=[('present', 'Present'), ('absent', 'Absent'), ('leave', 'On Leave'), ('late', 'Late')], default='present', max_length=20)),
                ('location_ip', models.CharField(blank=True, max_length=80)),
                ('last_activity', models.DateTimeField(blank=True, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attendance_logs', to='hr.externalemployee')),
                ('marked_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='external_attendance_marked', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date', 'employee__full_name'],
                'unique_together': {('employee', 'date')},
            },
        ),
    ]
