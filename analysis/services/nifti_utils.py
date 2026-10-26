"""NIfTI validation without reorientation or implicit registration."""
import gzip
import math
from pathlib import Path
import nibabel as nib
import numpy as np
from django.conf import settings
from .errors import InvalidMRI


def load_volume(path):
    try:
        path = Path(path)
        if path.name.lower().endswith('.gz'):
            # Read incrementally to cap decompression bombs, including trailing payload.
            total = 0
            with gzip.open(path, 'rb') as stream:
                while chunk := stream.read(1024 * 1024):
                    total += len(chunk)
                    if total > settings.MAX_UNCOMPRESSED_MRI_MB * 1024 * 1024:
                        raise InvalidMRI('The expanded NIfTI file exceeds the allowed size.')
        elif path.stat().st_size > settings.MAX_UNCOMPRESSED_MRI_MB * 1024 * 1024:
            raise InvalidMRI('The NIfTI file exceeds the allowed size.')
        image = nib.load(path)
        if not isinstance(image, (nib.Nifti1Image, nib.Nifti2Image)):
            raise InvalidMRI('Upload a valid NIfTI volume.')
        if len(image.shape) != 3 or min(image.shape) < 2:
            raise InvalidMRI('Each modality must be a three-dimensional MRI volume.')
        if math.prod(image.shape) > settings.MAX_VOLUME_VOXELS or image.shape[2] > settings.MAX_VOLUME_SLICES:
            raise InvalidMRI('MRI dimensions exceed the workstation limits.')
        if not np.isfinite(image.affine).all() or abs(np.linalg.det(image.affine[:3, :3])) < 1e-10:
            raise InvalidMRI('The MRI spatial transform is invalid.')
        if nib.aff2axcodes(image.affine)[2] not in ('S', 'I'):
            raise InvalidMRI('Volumes must have axial slices along their third axis. Reorient both inputs together before uploading.')
        data = image.get_fdata(dtype=np.float64)
        if not np.isfinite(data).all():
            raise InvalidMRI('MRI contains non-finite intensities.')
        if not np.any(data):
            raise InvalidMRI('MRI contains no non-zero signal.')
        return image, data
    except InvalidMRI:
        raise
    except Exception as exc:
        raise InvalidMRI('The uploaded file could not be read as a valid NIfTI volume.') from exc


def load_pair(flair_path, t1ce_path):
    flair_image, flair = load_volume(flair_path)
    t1ce_image, t1ce = load_volume(t1ce_path)
    if flair.shape != t1ce.shape:
        raise InvalidMRI('Volume mismatch: FLAIR and T1ce dimensions do not match.')
    if not np.allclose(flair_image.affine, t1ce_image.affine, atol=1e-4, rtol=1e-5):
        raise InvalidMRI('Volume mismatch: spatial transforms differ. Upload co-registered modalities.')
    return flair_image, flair, t1ce
