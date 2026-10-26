import uuid
from django.conf import settings
from django.db import models


def scan_path(instance, filename):
    extension = '.nii.gz' if filename.lower().endswith('.nii.gz') else '.nii'
    return f'scans/{instance.id}/{uuid.uuid4().hex}{extension}'


class MRIAnalysis(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    flair_file = models.FileField(upload_to=scan_path)
    t1ce_file = models.FileField(upload_to=scan_path)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.QUEUED, db_index=True)
    stage = models.CharField(max_length=80, default='Waiting for analysis worker')
    model_version = models.CharField(max_length=100)
    inference_time = models.FloatField(null=True, blank=True)
    number_of_slices = models.PositiveIntegerField(default=0)
    processed_slices = models.PositiveIntegerField(default=0)
    selected_slice = models.PositiveIntegerField(default=0)
    threshold = models.FloatField(default=0.5)
    result_metadata = models.JSONField(default=dict)
    error_message = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def display_id(self):
        return f'SCAN-{str(self.id)[:8].upper()}'
