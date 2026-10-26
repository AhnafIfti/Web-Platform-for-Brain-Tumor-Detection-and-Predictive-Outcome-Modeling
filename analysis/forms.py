from django import forms
from django.conf import settings


class MRIUploadForm(forms.Form):
    flair_file = forms.FileField(label='FLAIR MRI')
    t1ce_file = forms.FileField(label='T1ce / T1c MRI')
    research_consent = forms.BooleanField(label='I understand these outputs are educational and are not a medical diagnosis.')

    def clean(self):
        values = super().clean()
        for field in ('flair_file', 't1ce_file'):
            upload = values.get(field)
            if upload:
                if not upload.name.lower().endswith(settings.ALLOWED_MRI_EXTENSIONS):
                    self.add_error(field, 'Upload a NIfTI .nii or .nii.gz volume.')
                elif upload.size == 0 or upload.size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    self.add_error(field, f'File must be non-empty and smaller than {settings.MAX_UPLOAD_SIZE_MB} MB.')
        return values
