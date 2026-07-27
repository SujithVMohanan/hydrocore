import argparse

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.analytics.models import RainfallEvent
from apps.basin.models import Basin
from apps.observations.models import MeasurementType, Observation
from apps.users.models import Users


class Command(BaseCommand):
    help = "Delete non-user model data while preserving Users and related auth data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip the confirmation prompt and delete the data immediately",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without making changes",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        dry_run = options.get("dry_run", False)

        models_to_clear = [
            RainfallEvent,
            Observation,
            MeasurementType,
            Basin,
        ]

        total_count = 0
        for model in models_to_clear:
            total_count += model.objects.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No non-user model data found to delete."))
            return

        self.stdout.write(
            self.style.WARNING(
                f"This will delete {total_count} records from non-user models "
                f"({', '.join(model.__name__ for model in models_to_clear)})"
            )
        )
        self.stdout.write(self.style.WARNING("Users and auth-related data will be preserved."))

        if not force and not dry_run:
            answer = input("Type 'yes' to continue: ").strip().lower()
            if answer != "yes":
                raise CommandError("Deletion cancelled.")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No data was deleted."))
            return

        with transaction.atomic():
            for model in models_to_clear:
                deleted_count, _ = model.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {deleted_count} rows from {model.__name__}")
                )

        self.stdout.write(self.style.SUCCESS("Non-user model data deletion complete."))
