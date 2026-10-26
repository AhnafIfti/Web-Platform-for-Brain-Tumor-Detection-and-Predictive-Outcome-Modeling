import csv
import logging
import math
from django.conf import settings

logger = logging.getLogger(__name__)
METRICS = ('Dice_WT', 'Dice_TC', 'Dice_ET', 'Avg_Dice')


def read_benchmarks():
    path = settings.BENCHMARK_CSV
    if not path.is_file():
        return [], 'No benchmark file has been configured.'
    try:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if not {'Model', 'Dataset', *METRICS}.issubset(reader.fieldnames or []):
                raise ValueError('Missing columns')
            rows = []
            for row in reader:
                values = {key: float(row[key]) for key in METRICS}
                if not all(math.isfinite(v) and 0 <= v <= 1 for v in values.values()):
                    raise ValueError('Invalid Dice value')
                rows.append({'Model': row['Model'], 'Dataset': row['Dataset'], **values})
            return rows, ''
    except (ValueError, OSError, KeyError, csv.Error):
        logger.exception('Invalid benchmark CSV')
        return [], 'The benchmark file could not be validated. Ask the administrator to check the CSV.'
