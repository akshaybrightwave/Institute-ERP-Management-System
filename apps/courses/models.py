from django.db import models
from apps.soft_delete import SoftDeleteModel
from apps.centers.models import Center
from apps.categories.models import Category


class Course(SoftDeleteModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )
    center = models.ForeignKey(
        Center,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255)
    duration = models.CharField(max_length=100)
    fees = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return self.name
