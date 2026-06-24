from django.db import models
from apps.soft_delete import SoftDeleteModel
from apps.centers.models import Center


class Course(SoftDeleteModel):
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)
    duration = models.CharField(max_length=100)
    fees = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return self.name
