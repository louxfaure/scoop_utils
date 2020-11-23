from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from cart_management.models import Person,PickupLocation, Items

class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    # def add_arguments(self, parser):
    #     parser.add_argument('poll_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        resas_ss_rdv = Items.objects.values('library_id','created' ).filter(appointment__isnull=True).aggregate(Max('created'))
        self.stdout.write(self.style.SUCCESS(resas_ss_rdv))
