import logging
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from .forms import MRIUploadForm
from .models import MRIAnalysis
from .services.errors import AnalysisError
from .services.model_loader import checkpoint_present
from .services.nifti_utils import load_pair
from .services.visualization import result_dir

logger = logging.getLogger(__name__)


@login_required
def new_analysis(request):
    return render(request, 'analysis/new.html', {'form': MRIUploadForm(), 'max_mb': settings.MAX_UPLOAD_SIZE_MB})


@require_POST
def create_analysis(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Sign in to upload MRI volumes.'}, status=401)
    form = MRIUploadForm(request.POST, request.FILES)
    if getattr(request, 'upload_limit_exceeded', False):
        return JsonResponse({'error': f'Each MRI must be smaller than {settings.MAX_UPLOAD_SIZE_MB} MB.'}, status=413)
    if not form.is_valid():
        return JsonResponse({'error': 'Please check the upload fields.', 'fields': form.errors.get_json_data()}, status=400)
    if not checkpoint_present():
        return JsonResponse({'error': 'Model unavailable: configure the trained Swin-Tiny checkpoint before starting an analysis.'}, status=503)
    analysis = MRIAnalysis(user=request.user, model_version=settings.MODEL_VERSION, threshold=settings.SEGMENTATION_THRESHOLD)
    try:
        analysis.flair_file.save(form.cleaned_data['flair_file'].name, form.cleaned_data['flair_file'], save=False)
        analysis.t1ce_file.save(form.cleaned_data['t1ce_file'].name, form.cleaned_data['t1ce_file'], save=False)
        load_pair(analysis.flair_file.path, analysis.t1ce_file.path)
        with transaction.atomic():
            # Serialize per-account queue limits under PostgreSQL.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if MRIAnalysis.objects.filter(user=request.user, status__in=['queued', 'processing']).count() >= settings.MAX_ACTIVE_ANALYSES_PER_USER:
                raise AnalysisError('Two analyses are already active. Wait for one to finish.')
            analysis.save()
    except Exception as exc:
        analysis.flair_file.delete(save=False)
        analysis.t1ce_file.delete(save=False)
        if not isinstance(exc, AnalysisError):
            logger.exception('Upload validation failed')
        message = str(exc) if isinstance(exc, AnalysisError) else 'The scan could not be saved. Please try again.'
        return JsonResponse({'error': message}, status=400)
    return JsonResponse({'analysis_id': str(analysis.id), 'status': analysis.status,
                         'url': reverse('analysis-detail', args=[analysis.id]),
                         'status_url': reverse('analysis-status', args=[analysis.id])}, status=202)


@login_required
def detail(request, pk):
    analysis = get_object_or_404(MRIAnalysis, pk=pk, user=request.user)
    return render(request, 'analysis/detail.html', {'analysis': analysis})


@login_required
@require_GET
def status(request, pk):
    analysis = get_object_or_404(MRIAnalysis, pk=pk, user=request.user)
    response = JsonResponse({'analysis_id': str(analysis.id), 'status': analysis.status, 'stage': analysis.stage,
                             'processed_slices': analysis.processed_slices, 'number_of_slices': analysis.number_of_slices,
                             'error': analysis.error_message, 'model': analysis.model_version,
                             'representative_slice': analysis.selected_slice,
                             'regions': analysis.result_metadata.get('regions', {}),
                             'inference_time_ms': analysis.result_metadata.get('inference_time_ms')})
    response['Cache-Control'] = 'no-store'
    return response


@login_required
def asset(request, pk, z, kind):
    analysis = get_object_or_404(MRIAnalysis, pk=pk, user=request.user, status='completed')
    if z >= analysis.number_of_slices or kind not in ('original', 'overlay', 'wt', 'tc', 'et'):
        raise Http404
    path = result_dir(pk) / f'{z}-{kind}.png'
    if not path.is_file():
        logger.warning('Missing result artifact for analysis %s slice %s kind %s', pk, z, kind)
        raise Http404
    response = FileResponse(path.open('rb'), content_type='image/png')
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def report(request, pk):
    analysis = get_object_or_404(MRIAnalysis, pk=pk, user=request.user, status='completed')
    from .services.reports import create_report
    document = create_report(analysis)
    if request.headers.get('Accept') == 'application/json':
        # Keep background export separate from navigation/download interception.
        import base64
        response = JsonResponse({'content': base64.b64encode(document.getvalue()).decode('ascii'),
                                 'filename': f'{analysis.display_id}-analysis-summary.pdf'})
        response['Cache-Control'] = 'private, no-store'
        return response
    response = FileResponse(document, content_type='application/pdf',
                            as_attachment=request.GET.get('inline') != '1',
                            filename=f'{analysis.display_id}-analysis-summary.pdf')
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
def history(request):
    items = MRIAnalysis.objects.filter(user=request.user)
    query, state = request.GET.get('q', '').strip()[:100], request.GET.get('status', '')
    if query:
        items = items.filter(id__icontains=query.removeprefix('SCAN-'))
    if state in MRIAnalysis.Status.values:
        items = items.filter(status=state)
    return render(request, 'analysis/history.html', {'page': Paginator(items, 15).get_page(request.GET.get('page')), 'query': query, 'state': state})


@login_required
@require_POST
def delete_analysis(request, pk):
    analysis = get_object_or_404(MRIAnalysis, pk=pk, user=request.user)
    if analysis.status in ('processing', 'queued'):
        return JsonResponse({'error': 'Wait for the active analysis to finish before deleting.'}, status=409)
    import shutil
    analysis.flair_file.delete(save=False)
    analysis.t1ce_file.delete(save=False)
    shutil.rmtree(result_dir(pk), ignore_errors=True)
    analysis.delete()
    return redirect('history')
