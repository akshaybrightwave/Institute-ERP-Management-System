from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone
from apps.soft_delete import SoftDeleteModel


# Create your models here.

from django.core.exceptions import ValidationError


class ActiveUserManager(UserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllUserManager(UserManager):
    pass


class User(AbstractUser):
    ROLE_CHOICES = (
        ('SUPER_ADMIN', 'Super Admin'),
        ('admin', 'Admin'),
        ('superadmin', 'Super Admin'),
        ('center', 'Center'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('hr', 'HR'),
        ('telecaller', 'Telecaller'),
        ('counselor', 'Counselor'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    center = models.OneToOneField(
        'centers.Center',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='center_user'
    )
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = ActiveUserManager()
    all_objects = AllUserManager()

    def clean(self):
        super().clean()
        if self.center and self.role != 'center':
            raise ValidationError({'center': "Only Center users can be assigned a Center."})

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'is_active', 'deleted_at'])
        return 1, {'accounts.User': 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class AuthActivityLog(models.Model):
    EVENT_CHOICES = (
        ('BOOTSTRAP_SUPER_ADMIN', 'Bootstrap Super Admin'),
        ('LOGIN_SUCCESS', 'Login Success'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('REGISTRATION_BLOCKED', 'Registration Blocked'),
        ('USER_CREATED', 'User Created'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('UNAUTHORIZED_ACCESS', 'Unauthorized Access'),
        ('SESSION_INVALID', 'Session Invalid'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auth_activity_logs'
    )
    username = models.CharField(max_length=150, blank=True)
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=255, blank=True)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['username', '-created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.username or 'anonymous'}"


class SuperAdminNotification(models.Model):
    TYPE_CHOICES = (
        ('USER_CREATED', 'New User Created'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('FOLLOWUP_OVERDUE', 'Follow-up Overdue'),
        ('EXPORT_COMPLETED', 'Export Completed'),
        ('SYSTEM_ALERT', 'System Alert'),
    )

    title = models.CharField(max_length=160)
    message = models.TextField(blank=True)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='SYSTEM_ALERT', db_index=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_superadmin_notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class SuperAdminExport(models.Model):
    STATUS_CHOICES = (
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('pending', 'Pending'),
    )
    FORMAT_CHOICES = (
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    )

    report_name = models.CharField(max_length=120)
    export_format = models.CharField(max_length=20, choices=FORMAT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed', db_index=True)
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='superadmin_exports'
    )
    file_name = models.CharField(max_length=180, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.report_name} ({self.export_format})"


class Feedback(SoftDeleteModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"
    
