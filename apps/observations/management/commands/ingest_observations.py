from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.observations.services.ingestion_errors import IngestionError
from apps.observations.services.ingestion_service import IngestionService
from apps.users.models import Users


class Command(BaseCommand):
    help = 'Ingest rainfall and/or temperature CSV observations'

    def add_arguments(self, parser):
        parser.add_argument('--rainfall', dest='rainfall', help='Path to rainfall CSV')
        parser.add_argument('--temperature', dest='temperature', help='Path to temperature CSV')
        parser.add_argument('--created-by', dest='created_by', type=int, default=None)
        parser.add_argument(
            '--no-auto-create-basins',
            action='store_true',
            help='Fail if CSV basin IDs are missing instead of creating them',
        )

    def handle(self, *args, **options):
        rainfall_path = options.get('rainfall')
        temperature_path = options.get('temperature')
        if not rainfall_path and not temperature_path:
            raise CommandError('Provide at least one of --rainfall or --temperature')

        created_by = None
        created_by_id = options.get('created_by')
        if created_by_id is not None:
            created_by = Users.objects.filter(id=created_by_id).first()
            if created_by is None:
                raise CommandError(f'No user found for id {created_by_id}')

        auto_create_basins = not options.get('no_auto_create_basins', False)

        try:
            if rainfall_path:
                self.stdout.write(self.style.NOTICE(f'Ingesting rainfall: {rainfall_path}'))
                with self._open_file(rainfall_path) as rainfall_file:
                    IngestionService.ingest_rainfall(
                        rainfall_file,
                        auto_create_basins=auto_create_basins,
                        created_by=created_by,
                    )

            if temperature_path:
                self.stdout.write(self.style.NOTICE(f'Ingesting temperature: {temperature_path}'))
                with self._open_file(temperature_path) as temperature_file:
                    IngestionService.ingest_temperature(
                        temperature_file,
                        auto_create_basins=auto_create_basins,
                        created_by=created_by,
                    )
        except IngestionError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS('Successfully created.'))

    @staticmethod
    def _open_file(path):
        file_path = Path(path).expanduser()
        if not file_path.exists():
            raise CommandError(f'File not found: {file_path}')
        return open(file_path, 'rb')
