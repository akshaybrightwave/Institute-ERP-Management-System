from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class FraudType(models.Model):
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Fraud Type'
        verbose_name_plural = 'Fraud Types'

    def __str__(self):
        return self.name


class PoliceStation(models.Model):
    name = models.CharField(max_length=180, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Police Station'
        verbose_name_plural = 'Police Stations'

    def __str__(self):
        return self.name


class RecoveryReport(models.Model):
    STATUS_DRAFT = 'Draft'
    STATUS_SUBMITTED = 'Submitted'
    STATUS_APPROVED = 'Approved'
    STATUS_REJECTED = 'Rejected'

    APPROVAL_STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    report_number = models.CharField(max_length=30, unique=True, editable=False)
    report_month = models.PositiveSmallIntegerField(db_index=True)
    report_year = models.PositiveSmallIntegerField(db_index=True)
    entry_date = models.DateField(default=timezone.localdate)
    name = models.CharField(max_length=180, blank=True)
    student = models.ForeignKey(
        'students.StudentAdmission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='investigator_recovery_reports'
    )
    police_station = models.ForeignKey(
        PoliceStation,
        on_delete=models.PROTECT,
        related_name='recovery_reports'
    )
    fraud_type = models.ForeignKey(
        FraudType,
        on_delete=models.PROTECT,
        related_name='recovery_reports'
    )
    mobile_recovery_count = models.PositiveIntegerField(default=0)
    financial_recovery_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_recovery_reports'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True
    )
    admin_remarks = models.TextField(blank=True)
    attachment = models.FileField(upload_to='investigator/recovery_reports/', null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval_status', '-created_at']),
            models.Index(fields=['report_year', 'report_month']),
        ]

    def __str__(self):
        return self.report_number

    @property
    def can_investigator_edit(self):
        return self.approval_status in {self.STATUS_DRAFT, self.STATUS_REJECTED}

    def save(self, *args, **kwargs):
        if not self.report_number:
            self.report_number = self.generate_report_number()
        super().save(*args, **kwargs)

    @classmethod
    def generate_report_number(cls):
        year = timezone.localdate().year
        prefix = f'INV-REC-{year}-'
        last_report = cls.objects.filter(report_number__startswith=prefix).order_by('-report_number').first()
        next_number = 1
        if last_report:
            try:
                next_number = int(last_report.report_number.rsplit('-', 1)[1]) + 1
            except (IndexError, ValueError):
                next_number = cls.objects.filter(report_number__startswith=prefix).count() + 1
        return f'{prefix}{next_number:04d}'


class CaseWorkReport(models.Model):
    STATUS_DRAFT = 'Draft'
    STATUS_SUBMITTED = 'Submitted'
    STATUS_APPROVED = 'Approved'
    STATUS_REJECTED = 'Rejected'

    APPROVAL_STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    CASE_PENDING = 'Pending'
    CASE_IN_PROGRESS = 'In Progress'
    CASE_COMPLETED = 'Completed'
    CASE_CLOSED = 'Closed'

    CASE_STATUS_CHOICES = [
        (CASE_PENDING, 'Pending'),
        (CASE_IN_PROGRESS, 'In Progress'),
        (CASE_COMPLETED, 'Completed'),
        (CASE_CLOSED, 'Closed'),
    ]

    report_number = models.CharField(max_length=32, unique=True, editable=False)
    name = models.CharField(max_length=180)
    case_no = models.CharField(max_length=120)
    police_station = models.ForeignKey(
        PoliceStation,
        on_delete=models.PROTECT,
        related_name='case_work_reports'
    )
    investigating_officer = models.CharField(max_length=180)
    case_status = models.CharField(max_length=20, choices=CASE_STATUS_CHOICES, default=CASE_PENDING, db_index=True)
    entry_date = models.DateField(default=timezone.localdate)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='submitted_case_work_reports'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True
    )
    admin_remarks = models.TextField(blank=True)
    attachment = models.FileField(upload_to='investigator/case_work_reports/', null=True, blank=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval_status', '-created_at']),
            models.Index(fields=['case_status', '-created_at']),
        ]

    def __str__(self):
        return self.report_number

    @property
    def can_investigator_edit(self):
        return self.approval_status in {self.STATUS_DRAFT, self.STATUS_REJECTED}

    def save(self, *args, **kwargs):
        if not self.report_number:
            self.report_number = self.generate_report_number()
        super().save(*args, **kwargs)

    @classmethod
    def generate_report_number(cls):
        year = timezone.localdate().year
        prefix = f'INV-CASE-{year}-'
        last_report = cls.objects.filter(report_number__startswith=prefix).order_by('-report_number').first()
        next_number = 1
        if last_report:
            try:
                next_number = int(last_report.report_number.rsplit('-', 1)[1]) + 1
            except (IndexError, ValueError):
                next_number = cls.objects.filter(report_number__startswith=prefix).count() + 1
        return f'{prefix}{next_number:04d}'


class CaseWorkItem(models.Model):
    case_report = models.ForeignKey(
        CaseWorkReport,
        on_delete=models.CASCADE,
        related_name='work_items'
    )
    work_title = models.CharField(max_length=180)
    work_description = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.work_title
