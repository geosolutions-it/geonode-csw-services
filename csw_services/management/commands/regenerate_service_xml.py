from django.core.management.base import BaseCommand

from csw_services.models import CswService, update_metadata_document


class Command(BaseCommand):
    help = "Re-create the XML metadata documents of the CSW services"

    def add_arguments(self, parser):
        parser.add_argument(
            "-i", "--id", dest="ids", type=int, action="append", help="Only process the services with this id"
        )
        parser.add_argument(
            "-d", "--dry-run", dest="dry_run", action="store_true", help="Do not actually perform any change"
        )

    def handle(self, ids=None, dry_run=False, **options):
        services = CswService.objects.order_by("id")
        if ids:
            services = services.filter(id__in=ids)
            for missing in sorted(set(ids) - set(services.values_list("id", flat=True))):
                self.stderr.write(f"Service not found: {missing}")

        ok = bad = 0
        for service in services:
            self.stdout.write(f"- {service.id} [{service.service_type}] {service.uuid} '{service.title}'")
            if dry_run:
                ok += 1
                continue
            try:
                update_metadata_document(service)
                ok += 1
            except Exception as e:
                self.stderr.write(f"  Error regenerating the metadata of service {service.id}: {e}")
                bad += 1

        self.stdout.write(f"{'Would regenerate' if dry_run else 'Regenerated'} {ok} services, {bad} errors")
