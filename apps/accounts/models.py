from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.

from django.core.exceptions import ValidationError

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Super Admin'),
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

    def clean(self):
        super().clean()
        if self.center and self.role != 'center':
            raise ValidationError({'center': "Only Center users can be assigned a Center."})



class Feedback(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.subject}"
    
