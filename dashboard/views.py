from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import render
from analysis.models import MRIAnalysis


@login_required
def overview(request):
    items = MRIAnalysis.objects.filter(user=request.user)
    completed = items.filter(status='completed')
    return render(request, 'dashboard/overview.html', {'total': items.count(), 'completed': completed.count(),
                  'average': completed.aggregate(value=Avg('inference_time'))['value'], 'recent': items[:5]})


@login_required
def research(request):
    return render(request, 'dashboard/research.html')


@login_required
def preferences(request):
    return render(request, 'dashboard/settings.html', {'threshold': settings.SEGMENTATION_THRESHOLD,
                  'max_mb': settings.MAX_UPLOAD_SIZE_MB, 'device': settings.MODEL_DEVICE})
