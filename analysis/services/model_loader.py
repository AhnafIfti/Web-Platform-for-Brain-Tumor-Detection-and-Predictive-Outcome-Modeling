import hashlib
import logging
import threading
import torch
from django.conf import settings
from ml_models.model_definition import build_model
from .errors import ModelUnavailable

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_loaded = None


def checkpoint_present():
    return settings.MODEL_CHECKPOINT_PATH.is_file()


def get_model():
    """Load trusted operator-provided tensor weights once per worker process."""
    global _loaded
    if _loaded is not None:
        return _loaded
    with _lock:
        if _loaded is not None:
            return _loaded
        if not checkpoint_present():
            raise ModelUnavailable('Model unavailable: the trained Swin-Tiny checkpoint has not been configured.')
        try:
            device = torch.device(('cuda' if torch.cuda.is_available() else 'cpu')
                                  if settings.MODEL_DEVICE == 'auto' else settings.MODEL_DEVICE)
            checkpoint = torch.load(settings.MODEL_CHECKPOINT_PATH, map_location='cpu', weights_only=True)
            state = checkpoint
            if isinstance(checkpoint, dict):
                state = checkpoint.get('state_dict', checkpoint.get('model_state_dict', checkpoint))
            model = build_model()
            model.load_state_dict(state, strict=True)
            model.to(device).eval()
            with open(settings.MODEL_CHECKPOINT_PATH, 'rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            _loaded = (model, device, digest)
            return _loaded
        except Exception as exc:
            logger.exception('Unable to load configured checkpoint')
            raise ModelUnavailable('Model unavailable: checkpoint or architecture is incompatible. Ask the administrator to verify the model configuration.') from exc
