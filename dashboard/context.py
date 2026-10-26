from django.conf import settings


def brand(request):
    return {'checkpoint_present': settings.MODEL_CHECKPOINT_PATH.is_file(), 'model_version': settings.MODEL_VERSION,
            'registration_enabled': settings.REGISTRATION_ENABLED}
