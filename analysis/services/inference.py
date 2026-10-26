import logging
import shutil
import time
import numpy as np
import nibabel as nib
import torch
from django.conf import settings
from django.utils import timezone
from analysis.models import MRIAnalysis
from .errors import AnalysisError
from .model_loader import get_model
from .nifti_utils import load_pair
from .preprocessing import prepare_slice
from .visualization import result_dir, save_slice

logger = logging.getLogger(__name__)


def update(analysis, **values):
    values['updated_at'] = timezone.now()
    MRIAnalysis.objects.filter(pk=analysis.pk).update(**values)
    for key, value in values.items():
        setattr(analysis, key, value)


def infer_probabilities(model, tensor, device):
    with torch.inference_mode():
        logits = model(tensor.to(device))
        if tuple(logits.shape) != (1, 3, 224, 224) or not torch.isfinite(logits).all():
            raise AnalysisError('Inference failed: model output is invalid.')
        return torch.sigmoid(logits)[0].cpu().numpy()


def process_analysis(analysis):
    """Worker service. Never selects slices using ground truth or fabricates results."""
    start = time.perf_counter()
    directory = result_dir(analysis.id)
    try:
        update(analysis, stage='Validating volumes')
        image, flair, t1ce = load_pair(analysis.flair_file.path, analysis.t1ce_file.path)
        update(analysis, stage='Loading neural network', number_of_slices=flair.shape[2])
        model, device, digest = get_model()
        update(analysis, model_version=settings.MODEL_VERSION)
        directory.mkdir(parents=True, exist_ok=True)
        statistics = []
        peaks = np.zeros(3, dtype=np.float64)
        voxel_counts = np.zeros(3, dtype=np.int64)
        representative_score, representative_slice = -1.0, 0
        inference_seconds = 0.0
        for z in range(flair.shape[2]):
            update(analysis, stage='Preprocessing slices')
            tensor = prepare_slice(flair[:, :, z], t1ce[:, :, z])
            nonempty = bool(np.any(flair[:, :, z]) or np.any(t1ce[:, :, z]))
            update(analysis, stage='Running neural network')
            if nonempty:
                tick = time.perf_counter()
                probabilities = infer_probabilities(model, tensor, device)
                inference_seconds += time.perf_counter() - tick
            else:
                probabilities = np.zeros((3, 224, 224), dtype=np.float32)
            update(analysis, stage='Generating segmentation')
            np.save(directory / f'{z}-probabilities.npy', probabilities, allow_pickle=False)
            masks = probabilities >= analysis.threshold
            np.save(directory / f'{z}-masks.npy', masks, allow_pickle=False)
            areas = masks.sum(axis=(1, 2))
            slice_peaks = probabilities.max(axis=(1, 2))
            peaks = np.maximum(peaks, slice_peaks)
            voxel_counts += areas
            score = float(probabilities[0].sum())
            if nonempty and score > representative_score:
                representative_score, representative_slice = score, z
            statistics.append({'slice': z, 'processed': nonempty, 'areas': areas.tolist(), 'peaks': slice_peaks.tolist()})
            save_slice(directory, z, tensor, probabilities, analysis.threshold)
            update(analysis, processed_slices=z + 1)
        update(analysis, stage='Preparing visualization')
        metadata = {
            'regions': {name: {'peak_probability': float(peaks[c]), 'model_grid_voxels': int(voxel_counts[c])}
                        for c, name in enumerate(('wt', 'tc', 'et'))},
            'slices': statistics, 'original_shape': list(flair.shape),
            'affine': image.affine.tolist(), 'orientation': list(nib.aff2axcodes(image.affine)),
            'spacing': [float(x) for x in image.header.get_zooms()],
            'model_grid': [224, 224], 'checkpoint_sha256': digest,
            'threshold': analysis.threshold, 'normalization': 'notebook-cell-16-constant-safe-v1',
            'representative_method': 'maximum summed WT segmentation probability',
            'duration_seconds': round(time.perf_counter() - start, 3),
            'inference_time_ms': round(inference_seconds * 1000, 2),
            'units': 'Counts and areas are on the 224x224 model grid, not physical tumor volume.',
        }
        update(analysis, status='completed', stage='Completed', result_metadata=metadata,
               selected_slice=representative_slice, inference_time=inference_seconds)
    except Exception as exc:
        logger.exception('Analysis %s failed', analysis.id)
        if directory.exists():
            shutil.rmtree(directory)
        message = str(exc) if isinstance(exc, AnalysisError) else 'The analysis could not be completed. Contact the administrator.'
        update(analysis, status='failed', stage='Analysis failed', error_message=message)
