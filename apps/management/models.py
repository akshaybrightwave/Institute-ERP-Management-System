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

    full_name = models.CharField(max_length=100, db_index=True)
    mobile_number = models.CharField(max_length=15, db_index=True)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100)
    course_interest = models.CharField(max_length=100)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='Website')
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='New', db_index=True)
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
        ('Closed', 'Closed'),
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
    )

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    followup_date = models.DateField()
    next_followup_date = models.DateField(null=True, blank=True)
    response = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Pending')
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

    def __str__(self):
        return f"FollowUp for {self.lead.inquiry.full_name} on {self.followup_date} ({self.status})"
