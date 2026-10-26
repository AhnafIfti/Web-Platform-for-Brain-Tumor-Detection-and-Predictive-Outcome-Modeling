import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from django.utils import timezone
from analysis.models import MRIAnalysis
from analysis.services.inference import process_analysis


class Command(BaseCommand):
    help = 'Process durable queued analyses. Run one worker per configured device.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')

    def handle(self, *args, **options):
        self.stdout.write('NeuroVision analysis worker ready. Ctrl+C to stop.')
        try:
            while True:
                close_old_connections()
                candidate = MRIAnalysis.objects.filter(status='queued').order_by('created_at').first()
                if candidate:
                    claimed = MRIAnalysis.objects.filter(pk=candidate.pk, status='queued').update(
                        status='processing', stage='Validating volumes', updated_at=timezone.now())
                    if claimed:
                        process_analysis(candidate)
                elif options['once']:
                    return
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write('Worker stopped. See README for interrupted-job recovery.')
