from django.db import models
from apps.soft_delete import SoftDeleteModel


class Center(SoftDeleteModel):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name
