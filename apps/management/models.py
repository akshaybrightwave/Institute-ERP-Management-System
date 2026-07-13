from django.db import models
from django.conf import settings
from django.utils import timezone
import datetime
from apps.soft_delete import SoftDeleteModel

class Inquiry(SoftDeleteModel):
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
        ('NO_ANSWER', 'Ringing'),
        ('CALL_BACK', 'Call Back'),
        ('CALL_DISCONNECTED', 'Call Disconnected'),
        ('WRONG_NUMBER', 'Wrong Number'),
        ('INTERESTED', 'Interested'),
        ('SWITCHED_OFF', 'Switched Off'),
        ('PENDING_FOLLOW_UP', 'Pending Follow Up'),
        ('OTHER', 'Other'),
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
        indexes = [
            models.Index(fields=['is_deleted', 'created_at'], name='mg_inquiry_del_created_idx'),
            models.Index(fields=['is_deleted', 'call_status'], name='mg_inquiry_del_call_idx'),
            models.Index(fields=['is_deleted', 'status'], name='mg_inquiry_del_status_idx'),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.status})"


class Lead(SoftDeleteModel):
    STATUS_CHOICES = (
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Interested', 'Interested'),
        ('Follow Up', 'Follow Up'),
        ('Qualified', 'Qualified'),
        ('Rejected', 'Rejected'),
        ('Invalid Number', 'Invalid Number'),

    )
    COUNSELOR_STATUS_CHOICES = (
        ('NEW', 'New'),
        ('CONTACTED', 'Contacted'),
        ('COUNSELING_DONE', 'Counseling Done'),
        ('FOLLOW_UP_REQUIRED', 'Follow Up Required'),
        ('INTERESTED', 'Interested'),
        ('CONVERTED', 'Converted'),
        ('ADMISSION', 'Admission'),
        ('NOT_INTERESTED', 'Not Interested'),
        ('LOST', 'Lost'),
    )
    PRIORITY_CHOICES = (
        ('Cold', 'Cold'),
        ('Warm', 'Warm'),
        ('Hot', 'Hot'),
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
    converted_at = models.DateTimeField(null=True, blank=True)
    telecaller_assigned_at = models.DateTimeField(null=True, blank=True)
    counselor_assigned_at = models.DateTimeField(null=True, blank=True)
    
    first_assigned_telecaller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='first_assigned_leads'
    )
    assigned_counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_counselor_leads'
    )
    first_assigned_counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='first_assigned_counselor_leads'
    )
    first_assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='globally_first_assigned_leads'
    )
    first_assigned_date = models.DateTimeField(null=True, blank=True)
    counselor_status = models.CharField(
        max_length=25,
        choices=COUNSELOR_STATUS_CHOICES,
        default='NEW',
        db_index=True
    )
    counselor_status_updated_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New', db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Warm', db_index=True)
    next_followup_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_deleted', 'created_at'], name='mg_lead_del_created_idx'),
            models.Index(fields=['is_deleted', 'assigned_at'], name='mg_lead_del_assigned_idx'),
            models.Index(fields=['is_deleted', 'converted_at'], name='mg_lead_del_converted_idx'),
            models.Index(fields=['is_deleted', 'assigned_counselor', 'converted_at'], name='mg_lead_counsel_conv_idx'),
            models.Index(fields=['is_deleted', 'assigned_telecaller', 'assigned_at'], name='mg_lead_tc_assigned_idx'),
            models.Index(fields=['is_deleted', 'first_assigned_user', 'converted_at'], name='mg_lead_owner_conv_idx'),
            models.Index(fields=['is_deleted', 'counselor_status', 'counselor_status_updated_at'], name='mg_lead_cstat_date_idx'),
        ]

    @property
    def original_owner(self):
        return (
            self.first_assigned_user
            or self.first_assigned_telecaller
            or self.first_assigned_counselor
            or self.assigned_telecaller
            or self.assigned_counselor
        )

    @property
    def original_owner_date(self):
        return (
            self.first_assigned_date
            or self.telecaller_assigned_at
            or self.counselor_assigned_at
            or self.assigned_at
        )

    def _set_first_assignment_defaults(self):
        if self.assigned_telecaller_id and not self.first_assigned_telecaller_id:
            self.first_assigned_telecaller_id = self.assigned_telecaller_id

        if self.assigned_counselor_id and not self.first_assigned_counselor_id:
            self.first_assigned_counselor_id = self.assigned_counselor_id

        if not self.first_assigned_user_id:
            self.first_assigned_user_id = (
                self.first_assigned_telecaller_id
                or self.first_assigned_counselor_id
                or self.assigned_telecaller_id
                or self.assigned_counselor_id
            )

        if self.first_assigned_user_id and not self.first_assigned_date:
            if self.first_assigned_user_id == self.first_assigned_telecaller_id:
                self.first_assigned_date = self.telecaller_assigned_at or self.assigned_at or timezone.now()
            elif self.first_assigned_user_id == self.first_assigned_counselor_id:
                self.first_assigned_date = self.counselor_assigned_at or self.assigned_at or timezone.now()
            else:
                self.first_assigned_date = self.assigned_at or timezone.now()

    def save(self, *args, **kwargs):
        protected_field_map = {
            'first_assigned_user': 'first_assigned_user_id',
            'first_assigned_date': 'first_assigned_date',
            'first_assigned_telecaller': 'first_assigned_telecaller_id',
            'first_assigned_counselor': 'first_assigned_counselor_id',
            'converted_at': 'converted_at',
        }
        original_values = {}

        if self.pk:
            existing = Lead.objects.filter(pk=self.pk).only(
                'first_assigned_user',
                'first_assigned_date',
                'first_assigned_telecaller',
                'first_assigned_counselor',
                'converted_at',
            ).first()
            if existing:
                original_values = {
                    'first_assigned_user_id': existing.first_assigned_user_id,
                    'first_assigned_date': existing.first_assigned_date,
                    'first_assigned_telecaller_id': existing.first_assigned_telecaller_id,
                    'first_assigned_counselor_id': existing.first_assigned_counselor_id,
                    'converted_at': existing.converted_at,
                }

        before_values = {
            field_name: getattr(self, value_attr)
            for field_name, value_attr in protected_field_map.items()
        }

        self._set_first_assignment_defaults()

        changed_protected_fields = {
            field_name
            for field_name, value_attr in protected_field_map.items()
            if getattr(self, value_attr) != before_values[field_name]
        }

        for field_name, original_value in original_values.items():
            if original_value:
                current_value = getattr(self, field_name)
                if current_value != original_value:
                    setattr(self, field_name, original_value)
                    changed_protected_fields.add(field_name.replace('_id', ''))

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.update(changed_protected_fields)
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lead: {self.inquiry.full_name} ({self.status})"


class CallLog(SoftDeleteModel):
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
        indexes = [
            models.Index(fields=['is_deleted', 'call_date'], name='mg_call_del_date_idx'),
            models.Index(fields=['is_deleted', 'created_by'], name='mg_call_del_user_idx'),
        ]

    def __str__(self):
        return f"Call to {self.lead.inquiry.full_name} - {self.call_status}"


class FollowUp(SoftDeleteModel):
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
        indexes = [
            models.Index(fields=['is_deleted', 'status', 'followup_date'], name='mg_follow_del_status_idx'),
            models.Index(fields=['is_deleted', 'created_by', 'status', 'followup_date'], name='mg_follow_user_status_idx'),
        ]

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


class LeadImport(SoftDeleteModel):
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


class LeadNote(SoftDeleteModel):
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


class LeadActivity(SoftDeleteModel):
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


class ImportErrorLog(SoftDeleteModel):
    lead_import = models.ForeignKey(LeadImport, on_delete=models.CASCADE, related_name='error_logs')
    row_number = models.PositiveIntegerField()
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['row_number']

    def __str__(self):
        return f"ImportError in {self.lead_import} at row {self.row_number}: {self.error_message}"


class CounselingSession(SoftDeleteModel):
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


class VisitSheet(SoftDeleteModel):
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


class AdmissionSheet(SoftDeleteModel):
    ADMISSION_STATUS_CHOICES = (
        ('CONFIRMED', 'Confirmed'),
        ('PENDING', 'Pending'),
        ('CANCELLED', 'Cancelled'),
    )
    SEAT_STATUS_CHOICES = (
        ('BOOKED', 'Booked'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
    )
    DOCUMENT_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('RECEIVED', 'Received'),
        ('VERIFIED', 'Verified'),
    )
    FEE_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('PARTIAL', 'Partial'),
        ('PAID', 'Paid'),
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

    batch_name = models.CharField(max_length=100, blank=True)

    # Seat Information
    seat_status = models.CharField(
        max_length=20, choices=SEAT_STATUS_CHOICES, default='BOOKED', db_index=True
    )

    # Document & Fee Tracking
    document_status = models.CharField(
        max_length=20, choices=DOCUMENT_STATUS_CHOICES, default='PENDING', db_index=True
    )
    fee_status = models.CharField(
        max_length=20, choices=FEE_STATUS_CHOICES, default='PENDING', db_index=True
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

