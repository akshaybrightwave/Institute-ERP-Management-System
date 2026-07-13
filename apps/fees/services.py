from decimal import Decimal

from django.db import transaction

from .models import CenterPaymentSetting, StudentPaymentSetting


CENTER_PAYMENT_TYPES = [
    'Center Registration Fee',
    'Center Renewal Fee',
    'Center Security Deposit',
    'Certificate Fee',
    'License Renewal Fee',
]

STUDENT_PAYMENT_TYPES = [
    'Admission Fees',
    'Re-Admission Fees',
    'Exam Fees',
    'Re-Exam Fees',
    'ID Card Fees',
    'Certificate Fees',
    'Late Fees',
]


@transaction.atomic
def sync_center_payment_settings():
    created_count = 0
    for index, title in enumerate(CENTER_PAYMENT_TYPES, start=1):
        _, created = CenterPaymentSetting.objects.get_or_create(
            title=title,
            defaults={
                'amount': Decimal('0.00'),
                'is_visible': True,
                'sort_order': index,
            }
        )
        if created:
            created_count += 1
    return created_count


@transaction.atomic
def sync_student_payment_settings():
    created_count = 0
    for index, title in enumerate(STUDENT_PAYMENT_TYPES, start=1):
        _, created = StudentPaymentSetting.objects.get_or_create(
            title=title,
            defaults={
                'amount': Decimal('0.00'),
                'is_visible': True,
                'sort_order': index,
            }
        )
        if created:
            created_count += 1
    return created_count
