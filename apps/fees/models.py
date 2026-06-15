from django.db import models
from apps.students.models import StudentProfile


class FeePayment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('upi', 'UPI'),
        ('bank', 'Bank Transfer'),
    ]

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    payment_date = models.DateField()
    payment_method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True
    )
    remarks = models.TextField(
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.student.full_name} - ₹{self.amount} on {self.payment_date}"
