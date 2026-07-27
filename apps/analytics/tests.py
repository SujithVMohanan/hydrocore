from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Users
from apps.basin.models import Basin
from apps.analytics.models import RainfallEvent


class BaseRainfallEventApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = self.make_user()
        self.auth_client_inst = self.auth_client(self.user)

    def make_user(self, email="rain_user@example.com", password="Test@1234", **kwargs) -> Users:
        return Users.objects.create_user(email=email, password=password, **kwargs)

    def auth_client(self, user: Users) -> APIClient:
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def create_basin(self, name="Analytics Basin", **kwargs) -> Basin:
        return Basin.objects.create(name=name, **kwargs)

    def create_rainfall_event(
        self,
        basin,
        start_time=None,
        end_time=None,
        duration=12,
        peak=45.5,
        volume=120.0,
        dry_gap=6,
        is_cold=False,
    ) -> RainfallEvent:
        now = timezone.now()
        if start_time is None:
            start_time = now - timezone.timedelta(hours=12)
        if end_time is None:
            end_time = now
        return RainfallEvent.objects.create(
            basin=basin,
            start_timestamp=start_time,
            end_timestamp=end_time,
            duration_hours=duration,
            peak_value=peak,
            total_volume=volume,
            min_dry_gap_used=dry_gap,
            is_cold_event=is_cold,
            created_by=self.user,
        )


class TestGetRainfallEventsApi(BaseRainfallEventApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("rainfall-event-list")
        self.basin = self.create_basin(name="Event Basin")
        self.event1 = self.create_rainfall_event(
            basin=self.basin,
            peak=50.0,
            volume=150.0,
            dry_gap=6,
        )
        self.event2 = self.create_rainfall_event(
            basin=self.basin,
            start_time=timezone.now() - timezone.timedelta(hours=24),
            end_time=timezone.now() - timezone.timedelta(hours=12),
            peak=80.0,
            volume=200.0,
            dry_gap=12,
        )

    def test_get_rainfall_events_success(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data["data"])
        self.assertGreaterEqual(len(response.data["data"]["results"]), 2)

    def test_get_rainfall_events_unauthenticated_fails(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_rainfall_events(self):
        response = self.auth_client_inst.get(self.url, {"search": "50"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertGreaterEqual(len(results), 1)

    def test_filter_by_basin_id(self):
        response = self.auth_client_inst.get(self.url, {"basin_id": self.basin.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertGreaterEqual(len(results), 2)

    def test_filter_by_min_dry_gap_used(self):
        response = self.auth_client_inst.get(self.url, {"min_dry_gap_used": 12})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["min_dry_gap_used"], 12)

    def test_filter_by_id(self):
        response = self.auth_client_inst.get(self.url, {"id": self.event1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.event1.id)

    def test_filter_by_min_total_volume(self):
        response = self.auth_client_inst.get(self.url, {"min_total_volume": 180})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.event2.id)


class TestDeleteRainfallEventsApi(BaseRainfallEventApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("rainfall-event-delete")
        self.basin = self.create_basin(name="Delete Event Basin")

    def test_delete_rainfall_events_success(self):
        ev1 = self.create_rainfall_event(basin=self.basin, dry_gap=3)
        ev2 = self.create_rainfall_event(basin=self.basin, dry_gap=4)
        response = self.auth_client_inst.delete(
            self.url,
            {"ids": f"{ev1.id},{ev2.id}"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertFalse(RainfallEvent.objects.filter(id__in=[ev1.id, ev2.id]).exists())

    def test_delete_rainfall_events_unauthenticated_fails(self):
        ev = self.create_rainfall_event(basin=self.basin, dry_gap=5)
        response = self.client.delete(self.url, {"ids": f"{ev.id}"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_rainfall_events_missing_ids_fails(self):
        response = self.auth_client_inst.delete(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestTimeseriesAndDetectApi(BaseRainfallEventApiTest):
    def setUp(self):
        super().setUp()
        self.basin = self.create_basin(name="Detect Basin")
        # create measurement type for rainfall
        from apps.observations.models import MeasurementType, Observation

        self.mt = MeasurementType.objects.create(name="rainfall", unit="mm", created_by=self.user)
        # create hourly observations over 10 hours with pattern: 1,2,0,0,3,4,0,5,0,0
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        values = [1,2,0,0,3,4,0,5,0,0]
        self.observations = []
        for i, v in enumerate(values):
            ts = now - timezone.timedelta(hours=(len(values)-1-i))
            self.observations.append(Observation.objects.create(basin=self.basin, measurement_type=self.mt, timestamp=ts, value=v, created_by=self.user))

        self.timeseries_url = reverse('basin-timeseries', kwargs={"basin_id": self.basin.id})
        self.detect_url = reverse('basin-detect-events', kwargs={"basin_id": self.basin.id})

    def test_get_timeseries_requires_measurement_id(self):
        resp = self.auth_client_inst.get(self.timeseries_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_timeseries_success(self):
        resp = self.auth_client_inst.get(self.timeseries_url, {"measurement_id": self.mt.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data['data']
        self.assertIsInstance(data, dict)
        results = data.get('data') if data.get('data') else data.get('results')
        # Our wrapper returns data key with list
        # When using ResponseInfo.ok, data is the list under 'data'
        if isinstance(results, list):
            pts = results
        else:
            pts = resp.data['data']
        self.assertGreaterEqual(len(pts), 10)

    def test_get_timeseries_with_pdf_style_params(self):
        resp = self.auth_client_inst.get(
            self.timeseries_url,
            {
                "measurement_type": "rainfall",
                "from": (timezone.now() - timezone.timedelta(days=2)).isoformat(),
                "to": timezone.now().isoformat(),
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_detect_events_creates_events(self):
        # Use min_dry_gap_hours =2 which will split where two consecutive zeros exist
        resp = self.auth_client_inst.post(self.detect_url + "?min_dry_gap_hours=2", {"measurement_id": self.mt.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data['status'])
        result = resp.data['data']
        self.assertIn('total_events', result)
        self.assertGreaterEqual(result['total_events'], 1)
        # Check persisted events
        from apps.analytics.models import RainfallEvent
        evs = RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=2)
        self.assertEqual(evs.count(), result['total_events'])


class TestBasinEventSummaryApi(BaseRainfallEventApiTest):
    def setUp(self):
        super().setUp()
        self.basin = self.create_basin(name='Summary Basin')
        self.create_rainfall_event(
            basin=self.basin,
            duration=4,
            peak=20.0,
            volume=40.0,
            dry_gap=6,
        )
        self.create_rainfall_event(
            basin=self.basin,
            start_time=timezone.now() - timezone.timedelta(hours=48),
            end_time=timezone.now() - timezone.timedelta(hours=36),
            duration=12,
            peak=8.0,
            volume=90.0,
            dry_gap=6,
        )
        self.url = reverse('basin-event-summary', kwargs={'basin_id': self.basin.id})

    def test_event_summary_success(self):
        response = self.auth_client_inst.get(self.url, {'min_dry_gap_hours': 6})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['status'])
        data = response.data['data']
        self.assertEqual(data['total_events'], 2)
        self.assertEqual(data['min_dry_gap_hours'], 6)
        self.assertEqual(data['peak_event']['peak_value'], 20.0)
        self.assertEqual(data['longest_event']['duration_hours'], 12)
        self.assertIn('mean_duration', data)
        self.assertIn('mean_total_volume', data)

    def test_event_summary_basin_not_found(self):
        url = reverse('basin-event-summary', kwargs={'basin_id': 999999})
        response = self.auth_client_inst.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['status'])


class TestPdfStyleRainfallRoutes(BaseRainfallEventApiTest):
    def setUp(self):
        super().setUp()
        self.basin = self.create_basin(name='PDF Basin')
        self.event = self.create_rainfall_event(basin=self.basin, volume=55.0, dry_gap=6)

    def test_basin_event_list_pdf_path(self):
        url = reverse('basin-event-list-pdf', kwargs={'basin_id': self.basin.id})
        response = self.auth_client_inst.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.event.id)
