import io

from django.test import TestCase

from apps.basin.models import Basin
from apps.observations.models import Observation
from apps.observations.services.ingestion_errors import IngestionError
from apps.observations.services.ingestion_service import IngestionService
from apps.users.models import Users


class IngestionServiceTest(TestCase):
    def setUp(self):
        self.user = Users.objects.create_user(email='ingest@test.com', password='Test@1234')

    def _rain_csv(self, rows: str) -> io.BytesIO:
        return io.BytesIO(('datetime,value,basin\n' + rows).encode('utf-8'))

    def _temp_csv(self, rows: str) -> io.BytesIO:
        return io.BytesIO(('Datetime,Value,Basin.ID\n' + rows).encode('utf-8'))

    def test_ingest_rainfall_creates_observations(self):
        f = self._rain_csv(
            '2019-01-01,0,2046\n'
            '2019-01-01 01:00:00,2.5,2046\n'
        )
        IngestionService.ingest_rainfall(f, created_by=self.user)
        self.assertEqual(Observation.objects.count(), 2)
        self.assertTrue(Basin.objects.filter(basin_id='2046').exists())

    def test_reupload_does_not_duplicate(self):
        f = self._rain_csv('2019-01-01 01:00:00,1.0,2046\n')
        IngestionService.ingest_rainfall(f, created_by=self.user)
        IngestionService.ingest_rainfall(f, created_by=self.user)
        self.assertEqual(Observation.objects.count(), 1)

    def test_invalid_row_stops_ingestion(self):
        f = self._rain_csv('bad-date,1.0,2046\n2019-01-01 02:00:00,3.0,2046\n')
        with self.assertRaises(IngestionError):
            IngestionService.ingest_rainfall(f, created_by=self.user)
        self.assertEqual(Observation.objects.count(), 0)

    def test_ingest_temperature_parses_dd_mm_yyyy(self):
        f = self._temp_csv('01/01/2019 1:00,-5.5,2046\n')
        IngestionService.ingest_temperature(f, created_by=self.user)
        obs = Observation.objects.select_related('measurement_type').get()
        self.assertEqual(obs.measurement_type.name, 'Temperature')
        self.assertAlmostEqual(obs.value, -5.5)

    def test_unknown_basin_strict_mode_stops(self):
        f = self._rain_csv('2019-01-01 01:00:00,1.0,9999\n')
        with self.assertRaises(IngestionError):
            IngestionService.ingest_rainfall(
                f, auto_create_basins=False, created_by=self.user,
            )
        self.assertEqual(Observation.objects.count(), 0)
