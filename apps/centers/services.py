import uuid

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Center, CenterCertificate


def _generate_center_certificate_number():
    return f"CCERT-{uuid.uuid4().hex[:8].upper()}"


def create_center_certificate_for_center(center, created_by=None):
    """
    Create the default authorization certificate for a saved center.

    Returns (certificate, created). If a certificate already exists for the
    center, the existing record is returned and no duplicate is created.
    """
    if not center or not center.pk:
        raise ValueError("Center must be saved before creating a certificate.")

    with transaction.atomic():
        locked_center = Center.objects.select_for_update().get(pk=center.pk)
        existing_certificate = CenterCertificate.objects.filter(
            center=locked_center
        ).first()
        if existing_certificate:
            return existing_certificate, False

        for _ in range(10):
            certificate_number = _generate_center_certificate_number()
            if CenterCertificate.objects.filter(
                certificate_number=certificate_number
            ).exists():
                continue

            try:
                with transaction.atomic():
                    certificate = CenterCertificate.objects.create(
                        center=locked_center,
                        certificate_number=certificate_number,
                        issue_date=timezone.localdate(),
                        valid_upto=locked_center.valid_upto,
                        certificate_status='Active',
                        created_by=created_by,
                    )
                return certificate, True
            except IntegrityError:
                continue

    raise IntegrityError("Unable to generate a unique center certificate number.")
