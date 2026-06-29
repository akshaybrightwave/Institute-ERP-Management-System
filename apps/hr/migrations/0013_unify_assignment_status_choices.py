from django.db import migrations, models


PLACEMENT_STATUS_CHOICES = [
    ('scheduled', 'Scheduled'),
    ('appeared', 'Appeared'),
    ('absent', 'Absent'),
    ('selected', 'Selected'),
    ('rejected', 'Rejected'),
    ('pending', 'Pending'),
    ('joined', 'Joined'),
]

PROJECT_STATUS_CHOICES = [
    ('scheduled', 'Scheduled'),
    ('appeared', 'Appeared'),
    ('absent', 'Absent'),
    ('selected', 'Selected'),
    ('rejected', 'Rejected'),
    ('pending', 'Pending'),
    ('allocated', 'Allocated'),
    ('released', 'Released'),
]


def copy_final_status_to_assignment_status(apps, schema_editor):
    PlacementStudentAssignment = apps.get_model('hr', 'PlacementStudentAssignment')
    ProjectEmployeeAssignment = apps.get_model('hr', 'ProjectEmployeeAssignment')

    for assignment in PlacementStudentAssignment.objects.exclude(final_status='pending'):
        if assignment.final_status in dict(PLACEMENT_STATUS_CHOICES):
            assignment.interview_status = assignment.final_status
            assignment.save(update_fields=['interview_status'])

    for assignment in ProjectEmployeeAssignment.objects.exclude(final_status='pending'):
        if assignment.final_status in dict(PROJECT_STATUS_CHOICES):
            assignment.interview_status = assignment.final_status
            assignment.save(update_fields=['interview_status'])


class Migration(migrations.Migration):

    dependencies = [
        ('hr', '0012_candidate_salary_fields_to_charfield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='placementstudentassignment',
            name='interview_status',
            field=models.CharField(choices=PLACEMENT_STATUS_CHOICES, default='scheduled', max_length=20),
        ),
        migrations.AlterField(
            model_name='projectemployeeassignment',
            name='interview_status',
            field=models.CharField(choices=PROJECT_STATUS_CHOICES, default='scheduled', max_length=20),
        ),
        migrations.RunPython(copy_final_status_to_assignment_status, migrations.RunPython.noop),
    ]
