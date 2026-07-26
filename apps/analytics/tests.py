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
