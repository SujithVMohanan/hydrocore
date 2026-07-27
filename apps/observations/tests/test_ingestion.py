import io

from django.test import TestCase

from apps.basin.models import Basin
from apps.observations.models import Observation
from apps.observations.services.ingestion_service import IngestionService
from apps.users.models import Users


class IngestionServiceTest(TestCase):
    def setUp(self):
        self.user = Users.objects.create_user(email='ingest@test.com', password='Test@1234')

    def _rain_csv(self, rows: str) -> io.BytesIO:
        content = 'datetime,value,basin\n' + rows
        return io.BytesIO(content.encode('utf-8'))

    def _temp_csv(self, rows: str) -> io.BytesIO:
        content = 'Datetime,Value,Basin.ID\n' + rows
        return io.BytesIO(content.encode('utf-8'))

    def test_ingest_rainfall_creates_observations(self):
        f = self._rain_csv(
            '2019-01-01,0,2046\n'
            '2019-01-01 01:00:00,2.5,2046\n'
        )
        summary = IngestionService.ingest_rainfall(f, created_by=self.user)
        self.assertEqual(summary['rows_read'], 2)
        self.assertEqual(summary['rows_inserted'], 2)
        self.assertEqual(summary['rows_updated'], 0)
        self.assertEqual(summary['rows_ingested'], 2)
        self.assertEqual(summary['rows_not_inserted'], 0)
        self.assertEqual(summary['errors_count'], 0)
        self.assertEqual(Observation.objects.count(), 2)
        self.assertTrue(Basin.objects.filter(basin_id='2046').exists())

    def test_reupload_updates_instead_of_duplicating(self):
        f1 = self._rain_csv('2019-01-01 01:00:00,1.0,2046\n')
        IngestionService.ingest_rainfall(f1, created_by=self.user)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertAlmostEqual(Observation.objects.first().value, 1.0)

        f2 = self._rain_csv('2019-01-01 01:00:00,9.9,2046\n')
        summary = IngestionService.ingest_rainfall(f2, created_by=self.user)
        self.assertEqual(Observation.objects.count(), 1)
        self.assertEqual(summary['rows_inserted'], 0)
        self.assertEqual(summary['rows_updated'], 1)
        self.assertEqual(summary['rows_ingested'], 1)
        self.assertEqual(summary['rows_not_inserted'], 0)
        self.assertAlmostEqual(Observation.objects.first().value, 9.9)

    def test_error_summary_groups_by_code(self):
        f = self._rain_csv(
            'bad-date,1.0,2046\n'
            ',2.0,2046\n'
            '2019-01-01 02:00:00,3.0,2046\n'
        )
        summary = IngestionService.ingest_rainfall(f, created_by=self.user)
        self.assertEqual(summary['rows_not_inserted'], 2)
        self.assertEqual(summary['rows_ingested'], 1)
        self.assertEqual(summary['errors_count'], 2)
        self.assertEqual(summary['error_summary']['invalid_datetime'], 1)
        self.assertEqual(summary['error_summary']['invalid_value'], 1)
        self.assertEqual(summary['main_error']['code'], 'invalid_datetime')
        self.assertIn('error', summary['errors'][0])
        self.assertIn('function', summary['errors'][0])

    def test_build_simple_response(self):
        simple = IngestionService.build_simple_response({
            'rainfall': {
                'rows_read': 10,
                'rows_inserted': 8,
                'rows_updated': 2,
                'rows_ingested': 10,
                'rows_not_inserted': 0,
                'errors_count': 0,
                'error_summary': {},
                'errors': [],
                'errors_truncated': False,
                'duration_seconds': 1.5,
            }
        })
        self.assertTrue(simple['success'])
        self.assertEqual(simple['data']['rows_inserted'], 8)
        self.assertEqual(simple['data']['rows_saved'], 10)
        self.assertEqual(simple['errors'], [])

    def test_build_overall_summary(self):
        overall = IngestionService.build_overall_summary({
            'rainfall': {
                'rows_read': 10,
                'rows_inserted': 8,
                'rows_updated': 2,
                'rows_ingested': 10,
                'rows_not_inserted': 0,
                'errors_count': 0,
                'error_summary': {},
                'duration_seconds': 1.5,
            }
        })
        self.assertEqual(overall['rows_ingested'], 10)
        self.assertEqual(overall['files_processed'], ['rainfall'])

    def test_ingest_temperature_parses_dd_mm_yyyy(self):
        f = self._temp_csv('01/01/2019 1:00,-5.5,2046\n')
        summary = IngestionService.ingest_temperature(f, created_by=self.user)
        self.assertEqual(summary['rows_inserted'], 1)
        obs = Observation.objects.select_related('measurement_type').get()
        self.assertEqual(obs.measurement_type.name, 'Temperature')
        self.assertAlmostEqual(obs.value, -5.5)

    def test_invalid_row_is_skipped(self):
        f = self._rain_csv('bad-date,1.0,2046\n2019-01-01 02:00:00,3.0,2046\n')
        summary = IngestionService.ingest_rainfall(f, created_by=self.user)
        self.assertEqual(summary['rows_not_inserted'], 1)
        self.assertEqual(summary['errors_count'], 1)
        self.assertEqual(summary['error_summary']['invalid_datetime'], 1)
        self.assertEqual(Observation.objects.count(), 1)

    def test_unknown_basin_strict_mode(self):
        f = self._rain_csv('2019-01-01 01:00:00,1.0,9999\n')
        summary = IngestionService.ingest_rainfall(
            f, auto_create_basins=False, created_by=self.user,
        )
        self.assertEqual(summary['rows_not_inserted'], 1)
        self.assertEqual(summary['error_summary']['unknown_basin'], 1)
        self.assertEqual(Observation.objects.count(), 0)
