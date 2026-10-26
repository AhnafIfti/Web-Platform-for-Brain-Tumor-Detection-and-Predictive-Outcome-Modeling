from pathlib import Path
import numpy as np
from PIL import Image
from django.conf import settings

COLORS = np.array([[34, 211, 238], [245, 158, 11], [236, 72, 153]], dtype=np.uint8)


def result_dir(analysis_id):
    return Path(settings.MEDIA_ROOT) / 'results' / str(analysis_id)


def save_slice(directory, z, tensor, probabilities, threshold):
    original = np.clip(tensor[0, 0].numpy(), 0, 1)
    Image.fromarray((original * 255).astype(np.uint8)).save(directory / f'{z}-original.png')
    masks = probabilities >= threshold
    overlay = np.zeros((224, 224, 4), dtype=np.uint8)
    for c, name in enumerate(('wt', 'tc', 'et')):
        rgba = np.zeros_like(overlay)
        rgba[masks[c], :3] = COLORS[c]
        rgba[masks[c], 3] = 255
        Image.fromarray(rgba).save(directory / f'{z}-{name}.png')
        overlay[masks[c]] = rgba[masks[c]]
    Image.fromarray(overlay).save(directory / f'{z}-overlay.png')


def representative_image(analysis):
    directory = result_dir(analysis.id)
    original = Image.open(directory / f'{analysis.selected_slice}-original.png').convert('RGBA')
    overlay = Image.open(directory / f'{analysis.selected_slice}-overlay.png').convert('RGBA')
    overlay.putalpha(overlay.getchannel('A').point(lambda p: round(p * 0.65)))
    return Image.alpha_composite(original, overlay).convert('RGB')
