from django.core.management.base import BaseCommand, CommandError
from analysis.models import MRIAnalysis


class Command(BaseCommand):
    help = 'Requeue a specific interrupted analysis AFTER stopping its worker.'

    def add_arguments(self, parser):
        parser.add_argument('analysis_id')
        parser.add_argument('--worker-stopped', action='store_true')

    def handle(self, *args, **options):
        if not options['worker_stopped']:
            raise CommandError('Stop the worker first, then pass --worker-stopped.')
        count = MRIAnalysis.objects.filter(pk=options['analysis_id'], status__in=['processing', 'failed']).update(
            status='queued', stage='Waiting for analysis worker', processed_slices=0, error_message='')
        self.stdout.write(f'{count} analysis requeued.')
