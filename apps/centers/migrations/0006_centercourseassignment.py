"""
Migration: centers 0006_centercourseassignment

Phase 1 — Creates the CenterCourseAssignment table and migrates existing data:

1. Creates the CenterCourseAssignment table.
2. RunPython: copies Course.center FK relationships → CenterCourseAssignment rows.
3. RunPython: copies Center.assigned_courses M2M rows → CenterCourseAssignment
   (skips duplicates already created in step 2).

Backward compatible: does NOT remove Course.center or Center.assigned_courses.
"""

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrate_existing_relationships(apps, schema_editor):
    """
    Data migration: copies both sources into CenterCourseAssignment.
      Source 1 → Course.center FK  (every course with a center assigned)
      Source 2 → centers_center_assigned_courses M2M table (old simple M2M)
    """
    CenterCourseAssignment = apps.get_model('centers', 'CenterCourseAssignment')
    Course = apps.get_model('courses', 'Course')
    Center = apps.get_model('centers', 'Center')

    # ── Source 1: Course.center ForeignKey ───────────────────────────────────
    created_pairs = set()
    for course in Course.objects.filter(center__isnull=False).select_related('center'):
        key = (course.center_id, course.id)
        if key not in created_pairs:
            CenterCourseAssignment.objects.get_or_create(
                center_id=course.center_id,
                course_id=course.id,
                defaults={'is_active': True}
            )
            created_pairs.add(key)

    # ── Source 2: Center.assigned_courses M2M (centers_center_assigned_courses) ─
    for center in Center.objects.prefetch_related('assigned_courses'):
        for course in center.assigned_courses.all():
            key = (center.id, course.id)
            if key not in created_pairs:
                CenterCourseAssignment.objects.get_or_create(
                    center_id=center.id,
                    course_id=course.id,
                    defaults={'is_active': True}
                )
                created_pairs.add(key)


def reverse_migration(apps, schema_editor):
    """Reverse: delete all CenterCourseAssignment records (table is dropped anyway)."""
    CenterCourseAssignment = apps.get_model('centers', 'CenterCourseAssignment')
    CenterCourseAssignment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_alter_user_role'),
        ('centers', '0005_center_assigned_courses'),
        ('courses', '0004_alter_course_center'),
    ]

    operations = [
        # Step 1: Create the CenterCourseAssignment table
        migrations.CreateModel(
            name='CenterCourseAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True)),
                ('assigned_date', models.DateTimeField(auto_now_add=True)),
                ('assigned_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='course_assignments_made',
                    to='accounts.user'
                )),
                ('center', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='course_assignments',
                    to='centers.center'
                )),
                ('course', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assignments',
                    to='courses.course'
                )),
            ],
            options={
                'ordering': ['-assigned_date'],
                'unique_together': {('center', 'course')},
            },
        ),

        # Step 2: Copy existing relationships into the new table
        migrations.RunPython(
            migrate_existing_relationships,
            reverse_code=reverse_migration
        ),
    ]
