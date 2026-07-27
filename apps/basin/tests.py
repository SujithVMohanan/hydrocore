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


class BaseBasinApiTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = self.make_user()
        self.auth_client_inst = self.auth_client(self.user)

    def make_user(self, email="basin_user@example.com", password="Test@1234", **kwargs) -> Users:
        return Users.objects.create_user(email=email, password=password, **kwargs)

    def auth_client(self, user: Users) -> APIClient:
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def create_basin(self, name="Test Basin", **kwargs) -> Basin:
        return Basin.objects.create(name=name, created_by=self.user, **kwargs)

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

    def seed_hourly_rainfall(self, basin, measurement_type, values, start_ts=None):
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


class TestGetBasinsApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("basin-list")
        self.basin1 = self.create_basin(name="Alpha Station")
        self.basin2 = self.create_basin(name="Beta Station")

    def test_get_basins_success(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data["data"])
        self.assertGreaterEqual(len(response.data["data"]["results"]), 2)

    def test_get_basins_unauthenticated_fails(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_basins_by_name(self):
        response = self.auth_client_inst.get(self.url, {"search": "Alpha"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertGreaterEqual(len(results), 1)
        self.assertTrue(any("Alpha" in (r.get("name") or "") for r in results))

    def test_filter_basin_by_id(self):
        response = self.auth_client_inst.get(self.url, {"id": self.basin1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.basin1.id)


class TestCreateOrUpdateBasinApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("basin-create-or-update")

    def test_create_basin_success(self):
        response = self.auth_client_inst.post(
            self.url,
            {"name": "New Station", "metadata": {"source": "test"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["status"])
        self.assertTrue(Basin.objects.filter(name="New Station").exists())

    def test_update_basin_success(self):
        basin = self.create_basin(name="Old Name")
        response = self.auth_client_inst.post(
            self.url,
            {"id": basin.id, "name": "Updated Name", "metadata": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        basin.refresh_from_db()
        self.assertEqual(basin.name, "Updated Name")

    def test_update_basin_not_found(self):
        response = self.auth_client_inst.post(
            self.url,
            {"id": 999999, "name": "Missing", "metadata": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_basin_unauthenticated_fails(self):
        response = self.client.post(
            self.url,
            {"name": "No Auth", "metadata": {}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestDeleteBasinsApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("basin-delete")

    def test_delete_basins_success(self):
        b1 = self.create_basin(name="Del1")
        b2 = self.create_basin(name="Del2")
        response = self.auth_client_inst.delete(
            self.url,
            {"ids": f"{b1.id},{b2.id}"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertFalse(Basin.objects.filter(id__in=[b1.id, b2.id]).exists())

    def test_delete_basins_missing_ids_fails(self):
        response = self.auth_client_inst.delete(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_basins_unauthenticated_fails(self):
        basin = self.create_basin(name="NoAuthDel")
        response = self.client.delete(self.url, {"ids": f"{basin.id}"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestBasinEventsApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        self.basin = self.create_basin(name="Events Basin")
        self.event = self.create_rainfall_event(basin=self.basin, volume=55.0, dry_gap=6)
        self.url = reverse("basin-event-list-pdf", kwargs={"basin_id": self.basin.id})

    def test_basin_event_list_success(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.event.id)

    def test_basin_event_list_min_total_volume_filter(self):
        self.create_rainfall_event(basin=self.basin, volume=5.0, dry_gap=3)
        response = self.auth_client_inst.get(self.url, {"min_total_volume": 50})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.event.id)


class TestBasinEventSummaryApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        self.basin = self.create_basin(name="Summary Basin")
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
        self.url = reverse("basin-event-summary-pdf", kwargs={"basin_id": self.basin.id})

    def test_event_summary_success(self):
        response = self.auth_client_inst.get(self.url, {"min_dry_gap_hours": 6})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        data = response.data["data"]
        self.assertEqual(data["total_events"], 2)
        self.assertEqual(data["min_dry_gap_hours"], 6)
        self.assertEqual(data["peak_event"]["peak_value"], 20.0)
        self.assertEqual(data["longest_event"]["duration_hours"], 12)

    def test_event_summary_basin_not_found(self):
        url = reverse("basin-event-summary-pdf", kwargs={"basin_id": 999999})
        response = self.auth_client_inst.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["status"])


class TestBasinTimeseriesAndDetectApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        from apps.observations.models import MeasurementType, Observation

        self.basin = self.create_basin(name="Detect Basin")
        self.mt = MeasurementType.objects.create(name="rainfall", unit="mm", created_by=self.user)
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        values = [1, 2, 0, 0, 3, 4, 0, 5, 0, 0]
        for i, value in enumerate(values):
            Observation.objects.create(
                basin=self.basin,
                measurement_type=self.mt,
                timestamp=now - timezone.timedelta(hours=(len(values) - 1 - i)),
                value=value,
                created_by=self.user,
            )

        self.timeseries_url = reverse("basin-timeseries-pdf", kwargs={"basin_id": self.basin.id})
        self.detect_url = reverse("basin-detect-events-pdf", kwargs={"basin_id": self.basin.id})

    def test_get_timeseries_requires_measurement_id_or_type(self):
        resp = self.auth_client_inst.get(self.timeseries_url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_timeseries_success(self):
        resp = self.auth_client_inst.get(self.timeseries_url, {"measurement_id": self.mt.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        results = data.get("results") if isinstance(data, dict) else data
        if results is None and isinstance(data, dict):
            results = data.get("data", [])
        self.assertGreaterEqual(len(results), 10)

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

    def test_get_timeseries_no_data_in_requested_range(self):
        past_from = (timezone.now() - timezone.timedelta(days=30)).date().isoformat()
        past_to = (timezone.now() - timezone.timedelta(days=20)).date().isoformat()
        resp = self.auth_client_inst.get(
            self.timeseries_url,
            {"measurement_id": self.mt.id, "from": past_from, "to": past_to},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data["data"]
        results = data.get("results") if isinstance(data, dict) else data
        if results is None and isinstance(data, dict):
            results = data.get("data", [])
        self.assertEqual(results, [])

    def test_detect_events_creates_events(self):
        resp = self.auth_client_inst.post(
            f"{self.detect_url}?min_dry_gap_hours=2",
            {"measurement_id": self.mt.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["status"])
        result = resp.data["data"]
        self.assertIn("total_events", result)
        self.assertGreaterEqual(result["total_events"], 1)
        self.assertEqual(
            RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=2).count(),
            result["total_events"],
        )

    def test_redetect_via_api_keeps_same_count(self):
        first = self.auth_client_inst.post(
            f"{self.detect_url}?min_dry_gap_hours=2",
            {"measurement_id": self.mt.id},
            format="json",
        )
        second = self.auth_client_inst.post(
            f"{self.detect_url}?min_dry_gap_hours=2",
            {"measurement_id": self.mt.id},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["data"]["total_events"], second.data["data"]["total_events"])
        self.assertEqual(
            RainfallEvent.objects.filter(basin=self.basin, min_dry_gap_used=2).count(),
            second.data["data"]["total_events"],
        )


class TestBasinEventComparisonApi(BaseBasinApiTest):
    def setUp(self):
        super().setUp()
        self.basin = self.create_basin(name="Comparison Basin")
        self.create_rainfall_event(basin=self.basin, dry_gap=3, volume=10)
        self.create_rainfall_event(basin=self.basin, dry_gap=6, volume=20)
        self.url = reverse("basin-event-comparison-pdf", kwargs={"basin_id": self.basin.id})

    def test_event_comparison_success(self):
        response = self.auth_client_inst.get(self.url, {"gaps": "3,6"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        data = response.data["data"]
        self.assertEqual(data["basin_id"], self.basin.id)
        self.assertEqual(len(data["comparisons"]), 2)

    def test_event_comparison_missing_gaps_fails(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
