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
        ('admin', 'Admin'),
        ('center', 'Center'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
        ('hr', 'HR'),
        ('telecaller', 'Telecaller'),
        ('counselor', 'Counselor'),
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES)
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


class Feedback(SoftDeleteModel):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"
    
