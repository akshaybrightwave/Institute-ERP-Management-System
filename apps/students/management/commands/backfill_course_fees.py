"""
Management command: backfill_course_fees

One-time production backfill that permanently writes the correct historical
course fee (course_fee_at_admission) for every StudentProfile where the
field is currently NULL.

After this command runs successfully, ALL fee KPI calculations must use
StudentProfile.course_fee_at_admission exclusively.  No runtime fallback
to batch.course.fees should be necessary.

Usage:
    python manage.py backfill_course_fees [--dry-run]

Flags:
    --dry-run    Print what would be updated without saving to the database.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from apps.students.models import StudentProfile, StudentAdmission


class Command(BaseCommand):
    help = (
        "Permanently backfills course_fee_at_admission for StudentProfile "
        "records where the field is currently NULL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show which records would be updated without saving.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        null_qs = StudentProfile.objects.filter(
            course_fee_at_admission__isnull=True
        ).select_related("batch__course", "user")

        total = null_qs.count()

        if total == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    "No StudentProfile records with NULL course_fee_at_admission found. "
                    "Nothing to backfill."
                )
            )
            return

        self.stdout.write(
            f"Found {total} StudentProfile record(s) with NULL course_fee_at_admission."
        )

        to_update = []
        skipped = []

        for profile in null_qs:
            course_fee = None
            source = None

            # Source 1: batch -> course
            if profile.batch and profile.batch.course:
                course_fee = profile.batch.course.fees
                source = "batch.course.fees"

            # Source 2: StudentAdmission -> course (for students without a batch)
            if course_fee is None and profile.user_id:
                admission = (
                    StudentAdmission.objects
                    .select_related("course")
                    .filter(user=profile.user)
                    .first()
                )
                if not admission:
                    admission = (
                        StudentAdmission.objects
                        .select_related("course")
                        .filter(enrollment_no=profile.user.username)
                        .first()
                    )
                if admission and admission.course:
                    course_fee = admission.course.fees
                    source = "StudentAdmission.course.fees"

            if course_fee is None:
                # Cannot determine fee from any source — set to 0.00
                course_fee = Decimal("0.00")
                source = "no batch/course found — set to 0.00"
                skipped.append((profile.id, profile.full_name, source))

            self.stdout.write(
                f"  {'[DRY-RUN] ' if dry_run else ''}Student ID={profile.id} "
                f"({profile.full_name}): "
                f"course_fee_at_admission = {course_fee} [{source}]"
            )

            profile.course_fee_at_admission = course_fee
            to_update.append(profile)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry-run complete. {len(to_update)} record(s) would be updated. "
                    "No changes were saved."
                )
            )
        else:
            with transaction.atomic():
                StudentProfile.objects.bulk_update(
                    to_update, ["course_fee_at_admission"]
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nBackfill complete. {len(to_update)} record(s) updated successfully."
                )
            )

        if skipped:
            self.stdout.write(
                self.style.WARNING("\nStudents set to Rs.0.00 (no batch/course found):")
            )
            for sid, name, reason in skipped:
                self.stdout.write(f"  ID={sid} ({name}): {reason}")
