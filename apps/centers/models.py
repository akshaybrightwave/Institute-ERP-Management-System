from django.db import models


class Center(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name
