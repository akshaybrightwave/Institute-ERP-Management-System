from decimal import Decimal

from django.db import transaction

from .models import CenterPaymentSetting, StudentPaymentSetting


CENTER_PAYMENT_TYPES = [
    'Admission Fees',
    'Re-Admission Fees',
    'Exam Fees',
    'Re-Exam Fees',
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


def get_student_payment_amount(title):
    sync_student_payment_settings()
    setting = StudentPaymentSetting.objects.filter(title__iexact=title).first()
    if not setting or not setting.is_visible:
        return Decimal('0.00')
    return setting.amount or Decimal('0.00')


@transaction.atomic
def deduct_center_wallet_for_student_fee(center, title, quantity=1):
    amount = get_student_payment_amount(title) * Decimal(str(quantity or 0))
    if amount <= Decimal('0.00'):
        return Decimal('0.00')

    locked_center = center.__class__.objects.select_for_update().get(pk=center.pk)
    if amount > locked_center.wallet_balance:
        raise ValueError(
            f"Insufficient wallet balance. {title} is Rs.{amount:.2f}, "
            f"available balance is Rs.{locked_center.wallet_balance:.2f}."
        )

    locked_center.wallet_balance -= amount
    locked_center.save(update_fields=['wallet_balance'])
    center.wallet_balance = locked_center.wallet_balance
    return amount
