from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from .services import read_benchmarks, METRICS


@login_required
def overview(request):
    rows, error = read_benchmarks()
    datasets = sorted({row['Dataset'] for row in rows})
    selected = request.GET.get('dataset', '')
    query = request.GET.get('q', '')[:100]
    sort = request.GET.get('sort', 'Avg_Dice')
    if selected:
        rows = [r for r in rows if r['Dataset'] == selected]
    if query:
        rows = [r for r in rows if query.lower() in r['Model'].lower()]
    if sort not in METRICS:
        sort = 'Avg_Dice'
    rows.sort(key=lambda r: r[sort], reverse=True)
    return render(request, 'performance/overview.html', {'rows': rows, 'datasets': datasets, 'selected': selected,
                  'query': query, 'sort': sort, 'error': error, 'chart_data': rows,
                  'bundled_results': settings.BENCHMARK_CSV.resolve() == (settings.BASE_DIR / 'data/benchmarks/notebook_results.csv').resolve()})
