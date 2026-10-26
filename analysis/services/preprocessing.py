"""Notebook cell 16 preprocessing; no ImageNet normalization or GT selection."""
import numpy as np
import torch
import torch.nn.functional as F


def normalize_slice(array):
    array = np.asarray(array, dtype=np.float64)
    lo, hi = float(array.min()), float(array.max())
    if hi > 0:
        # Documented repair for the notebook's positive constant divide-by-zero.
        array = (array - lo) / (hi - lo) if hi > lo else np.zeros_like(array)
    return array.astype(np.float32)


def prepare_slice(flair, t1ce):
    stacked = np.stack([normalize_slice(flair), normalize_slice(t1ce)])
    tensor = torch.from_numpy(stacked).unsqueeze(0)
    return F.interpolate(tensor, size=(224, 224), mode='bilinear', align_corners=False)
