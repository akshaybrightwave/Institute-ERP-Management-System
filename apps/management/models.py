from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime

class Inquiry(models.Model):
    SOURCE_CHOICES = (
        ('Website', 'Website'),
        ('Walk-In', 'Walk-In'),
        ('Facebook', 'Facebook'),
        ('Instagram', 'Instagram'),
        ('Referral', 'Referral'),
        ('WhatsApp', 'WhatsApp'),
        ('Other', 'Other'),
    )
    STATUS_CHOICES = (
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Rejected', 'Rejected'),
    )
    CALL_STATUS_CHOICES = (
        ('NEW', 'New'),
        ('ACCEPTED', 'Accepted'),
        ('BUSY', 'Busy'),
        ('NO_ANSWER', 'No Answer'),
        ('CALL_BACK', 'Call Back'),
        ('WRONG_NUMBER', 'Wrong Number'),
        ('INTERESTED', 'Interested'),
        ('NOT_INTERESTED', 'Not Interested'),
    )

    full_name = models.CharField(max_length=100, db_index=True)
    mobile_number = models.CharField(max_length=15, db_index=True)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100)
    course_interest = models.CharField(max_length=100)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='Website')
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='New', db_index=True)
    call_status = models.CharField(max_length=25, choices=CALL_STATUS_CHOICES, default='NEW', db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_inquiries'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.status})"


class Lead(models.Model):
    STATUS_CHOICES = (
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Interested', 'Interested'),
        ('Follow Up', 'Follow Up'),
        ('Qualified', 'Qualified'),
        ('Rejected', 'Rejected'),
        ('Invalid Number', 'Invalid Number'),
        ('Admission Done', 'Admission Done'),
        ('Closed', 'Closed'),
    )
    COUNSELOR_STATUS_CHOICES = (
        ('NEW', 'New'),
        ('CONTACTED', 'Contacted'),
        ('COUNSELING_DONE', 'Counseling Done'),
        ('FOLLOW_UP_REQUIRED', 'Follow Up Required'),
        ('INTERESTED', 'Interested'),
        ('CONVERTED', 'Converted'),
        ('NOT_INTERESTED', 'Not Interested'),
        ('LOST', 'Lost'),
    )
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    )

    inquiry = models.OneToOneField(Inquiry, on_delete=models.CASCADE, related_name='lead')
    assigned_telecaller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_leads_by'
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    assigned_counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_counselor_leads'
    )
    counselor_status = models.CharField(
        max_length=25,
        choices=COUNSELOR_STATUS_CHOICES,
        default='NEW',
        db_index=True
    )
    counselor_status_updated_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium', db_index=True)
    next_followup_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Lead: {self.inquiry.full_name} ({self.status})"


class CallLog(models.Model):
    STATUS_CHOICES = (
        ('Connected', 'Connected'),
        ('Not Answered', 'Not Answered'),
        ('Busy', 'Busy'),
        ('Switched Off', 'Switched Off'),
        ('Invalid Number', 'Invalid Number'),
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='call_logs')
    call_date = models.DateTimeField(auto_now_add=True)
    call_duration = models.PositiveIntegerField(help_text="Duration in seconds")
    call_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_call_logs'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Call to {self.lead.inquiry.full_name} - {self.call_status}"


class FollowUp(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Missed', 'Missed'),
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    followup_date = models.DateField()
    next_followup_date = models.DateField(null=True, blank=True)
    response = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
    outcome = models.CharField(max_length=255, blank=True, null=True)
    reminder_sent = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_followups'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_overdue(self):
        return self.status == 'Pending' and self.followup_date < datetime.date.today()

    @property
    def days_overdue(self):
        if self.status == 'Pending' and self.followup_date < datetime.date.today():
            return (datetime.date.today() - self.followup_date).days
        return 0

    def __str__(self):
        return f"FollowUp for {self.lead.inquiry.full_name} on {self.followup_date} ({self.status})"


class LeadImport(models.Model):
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_imports'
    )
    file = models.FileField(upload_to='lead_imports/')
    total_records = models.PositiveIntegerField(default=0)
    successful_records = models.PositiveIntegerField(default=0)
    duplicate_records = models.PositiveIntegerField(default=0)
    failed_records = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Import by {self.uploaded_by} on {self.created_at}"


class LeadNote(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='notes_timeline')
    note = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_lead_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Note on {self.lead.inquiry.full_name} by {self.created_by} at {self.created_at}"


class LeadActivity(models.Model):
    ACTIVITY_TYPE_CHOICES = (
        ('LEAD_CREATED', 'Lead Created'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('CALL_LOG_ADDED', 'Call Log Added'),
        ('FOLLOWUP_CREATED', 'Follow-Up Created'),
        ('FOLLOWUP_COMPLETED', 'Follow-Up Completed'),
        ('NOTE_ADDED', 'Note Added'),
        ('ASSIGNED', 'Lead Assigned'),
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    description = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.activity_type} for {self.lead.inquiry.full_name} at {self.created_at}"


class ImportErrorLog(models.Model):
    lead_import = models.ForeignKey(LeadImport, on_delete=models.CASCADE, related_name='error_logs')
    row_number = models.PositiveIntegerField()
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"ImportError in {self.lead_import} at row {self.row_number}: {self.error_message}"


class CounselingSession(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='counseling_sessions')
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='counseling_sessions'
    )
    session_date = models.DateTimeField(default=timezone.now)
    discussion_notes = models.TextField()
    career_guidance_notes = models.TextField(blank=True)
    next_action = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-session_date']

    def __str__(self):
        return f"Session with {self.lead.inquiry.full_name} on {self.session_date}"


class VisitSheet(models.Model):
    STATUS_CHOICES = (
        ('Scheduled', 'Scheduled'),
        ('Visited', 'Visited'),
        ('No Show', 'No Show'),
        ('Cancelled', 'Cancelled'),
        ('Admission Done', 'Admission Done'),
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='visit_sheets', db_index=True)
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='counselor_visits',
        db_index=True
    )
    visit_date = models.DateField(db_index=True)
    visit_time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled', db_index=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_visits'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-visit_date', '-visit_time']

    def __str__(self):
        return f"Visit for {self.lead.inquiry.full_name} on {self.visit_date} at {self.visit_time}"


class AdmissionSheet(models.Model):
    ADMISSION_STATUS_CHOICES = (
        ('CONFIRMED', 'Confirmed'),
        ('PENDING_PAYMENT', 'Pending Payment'),
        ('CANCELLED', 'Cancelled'),
    )
    SEAT_STATUS_CHOICES = (
        ('BOOKED', 'Booked'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    )
    PAYMENT_MODE_CHOICES = (
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('CARD', 'Card'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('CHEQUE', 'Cheque'),
    )

    # Admission Information
    admission_number = models.CharField(max_length=20, unique=True, db_index=True)
    admission_date = models.DateField(default=datetime.date.today, db_index=True)
    admission_status = models.CharField(
        max_length=20, choices=ADMISSION_STATUS_CHOICES, default='CONFIRMED', db_index=True
    )

    # Student Information
    student_name = models.CharField(max_length=200)
    mobile_number = models.CharField(max_length=15)
    email_id = models.EmailField(blank=True, null=True)
    parent_name = models.CharField(max_length=200, blank=True)
    parent_mobile = models.CharField(max_length=15, blank=True)

    # Education Information
    college_name = models.CharField(max_length=300, blank=True)
    university_name = models.CharField(max_length=300, blank=True)
    department = models.CharField(max_length=200, blank=True)
    academic_year = models.CharField(max_length=20, blank=True)

    # Course Information
    course_name = models.CharField(max_length=200, blank=True)
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='counselor_admissions'
    )
    admission_source = models.CharField(max_length=100, blank=True)

    # Fee Information
    course_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    final_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fees_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_fees = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Payment Information
    payment_mode = models.CharField(
        max_length=20, choices=PAYMENT_MODE_CHOICES, default='CASH', blank=True
    )
    transaction_reference = models.CharField(max_length=100, blank=True)

    # Seat Information
    seat_status = models.CharField(
        max_length=20, choices=SEAT_STATUS_CHOICES, default='BOOKED', db_index=True
    )

    # Remarks
    remarks = models.TextField(blank=True)

    # System Fields
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='admission_sheet')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_admissions'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-admission_date', '-created_at']

    def __str__(self):
        return f"{self.admission_number} - {self.student_name}"

    def save(self, *args, **kwargs):
        # Auto-calculate remaining_fees
        self.remaining_fees = self.final_fees - self.fees_paid
        # Auto-generate admission_number if not set
        if not self.admission_number:
            year = datetime.date.today().year
            # Get the last admission number for this year
            last = AdmissionSheet.objects.filter(
                admission_number__startswith=f'ADM-{year}-'
            ).order_by('-admission_number').first()
            if last:
                last_num = int(last.admission_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            self.admission_number = f'ADM-{year}-{next_num:04d}'
        super().save(*args, **kwargs)

