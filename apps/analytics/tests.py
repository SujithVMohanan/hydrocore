from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Users
from apps.basin.models import Basin
from apps.analytics.models import RainfallEvent
from apps.analytics.services.rainfall_event_service import RainfallEventService


class BaseRainfallEventApiTest(TestCase):
    def setUp(self):
        cache.clear()
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
        response = self.auth_client_inst.get(
            self.url,
            {"basin_id": self.basin.id, "min_total_volume": 180},
        )
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


class DetectionAlgorithmTestMixin:

    def _seed_hourly_rainfall(self, basin, measurement_type, values, start_ts=None):
        from apps.observations.models import Observation

        start_ts = start_ts or timezone.now().replace(minute=0, second=0, microsecond=0)
        for i, value in enumerate(values):
            Observation.objects.create(
                basin=basin,
                measurement_type=measurement_type,
                timestamp=start_ts + timezone.timedelta(hours=i),
                value=value,
                created_by=self.user,
            )
        return start_ts


class TestDetectionAlgorithmCases(BaseRainfallEventApiTest, DetectionAlgorithmTestMixin):
   
    def setUp(self):
        super().setUp()
        from apps.observations.models import MeasurementType

        self.basin = self.create_basin(name="Detection Cases Basin")
        self.mt = MeasurementType.objects.create(
            name="Rainfall",
            unit="mm",
            created_by=self.user,
        )

    def test_detect_single_consecutive_nonzero_event(self):

        values = [1, 2, 3, 0, 0, 0, 0, 0, 0]
        self._seed_hourly_rainfall(self.basin, self.mt, values)

        result = RainfallEventService.detect_and_persist_events(
            basin_id=self.basin.id,
            min_dry_gap_hours=6,
            measurement_type_id=self.mt.id,
            created_by=self.user,
        )

        self.assertEqual(result["total_events"], 1)
        events = list(
            RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=6).order_by("start_timestamp")
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].duration_hours, 3)
        self.assertEqual(events[0].peak_value, 3.0)
        self.assertEqual(events[0].total_volume, 6.0)

    def test_detect_two_events_when_gap_meets_threshold(self):

        values = [1, 2, 0, 0, 0, 0, 0, 0, 4, 5]
        self._seed_hourly_rainfall(self.basin, self.mt, values)

        result = RainfallEventService.detect_and_persist_events(
            basin_id=self.basin.id,
            min_dry_gap_hours=6,
            measurement_type_id=self.mt.id,
            created_by=self.user,
        )

        self.assertEqual(result["total_events"], 2)
        events = list(
            RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=6).order_by("start_timestamp")
        )
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].total_volume, 3.0)
        self.assertEqual(events[1].total_volume, 9.0)

    def test_detect_merged_event_when_gap_shorter_than_threshold(self):

        values = [1, 2, 0, 0, 0, 3, 4]
        self._seed_hourly_rainfall(self.basin, self.mt, values)

        result = RainfallEventService.detect_and_persist_events(
            basin_id=self.basin.id,
            min_dry_gap_hours=6,
            measurement_type_id=self.mt.id,
            created_by=self.user,
        )

        self.assertEqual(result["total_events"], 1)
        events = list(
            RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=6).order_by("start_timestamp")
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].duration_hours, 7)
        self.assertEqual(events[0].peak_value, 4.0)
        self.assertEqual(events[0].total_volume, 10.0)



class TestDetectEventsIdempotencyService(BaseRainfallEventApiTest, DetectionAlgorithmTestMixin):
    def setUp(self):
        super().setUp()
        from apps.observations.models import MeasurementType

        self.basin = self.create_basin(name="Idempotent Detect Basin")
        self.mt = MeasurementType.objects.create(
            name="Rainfall",
            unit="mm",
            created_by=self.user,
        )
        values = [1, 2, 0, 0, 3, 4, 0, 0]
        self._seed_hourly_rainfall(self.basin, self.mt, values)

    def test_redetect_same_basin_gap_does_not_double_events(self):

        first = RainfallEventService.detect_and_persist_events(
            basin_id=self.basin.id,
            min_dry_gap_hours=2,
            measurement_type_id=self.mt.id,
            created_by=self.user,
        )
        second = RainfallEventService.detect_and_persist_events(
            basin_id=self.basin.id,
            min_dry_gap_hours=2,
            measurement_type_id=self.mt.id,
            created_by=self.user,
        )

        self.assertEqual(first["total_events"], second["total_events"])
        self.assertEqual(
            RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=2).count(),
            second["total_events"],
        )
        self.assertGreaterEqual(second["total_events"], 1)


class TestEventTimeseriesApi(BaseRainfallEventApiTest):
    def setUp(self):
        super().setUp()
        from apps.observations.models import MeasurementType, Observation

        self.basin = self.create_basin(name="Event Timeseries Basin")
        self.mt = MeasurementType.objects.create(name="Rainfall", unit="mm", created_by=self.user)
        start = timezone.now().replace(minute=0, second=0, microsecond=0) - timezone.timedelta(hours=3)
        for i, value in enumerate([1.0, 2.0, 0.0, 3.0]):
            Observation.objects.create(
                basin=self.basin,
                measurement_type=self.mt,
                timestamp=start + timezone.timedelta(hours=i),
                value=value,
                created_by=self.user,
            )
        self.event = self.create_rainfall_event(
            basin=self.basin,
            start_time=start,
            end_time=start + timezone.timedelta(hours=3),
            duration=4,
            peak=3.0,
            volume=6.0,
            dry_gap=6,
        )
        self.url = reverse("event-timeseries", kwargs={"event_id": self.event.id})

    def test_event_timeseries_success(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        results = data.get("results") if isinstance(data, dict) else data
        if results is None and isinstance(data, dict):
            results = data.get("data", [])
        self.assertGreaterEqual(len(results), 1)
