from django.conf import settings
from django.db import models


class RecoveryCodes(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    hashes = models.JSONField(default=list)
