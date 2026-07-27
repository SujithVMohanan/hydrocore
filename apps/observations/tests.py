import io
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Users
from apps.basin.models import Basin
from apps.observations.models import MeasurementType, Observation


class BaseObservationApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = self.make_user()
        self.auth_client_inst = self.auth_client(self.user)

    def make_user(self, email="obs_user@example.com", password="Test@1234", **kwargs) -> Users:
        return Users.objects.create_user(email=email, password=password, **kwargs)

    def auth_client(self, user: Users) -> APIClient:
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    def create_basin(self, name="Test Basin", **kwargs) -> Basin:
        return Basin.objects.create(name=name, **kwargs)

    def create_measurement_type(self, name="Precipitation", unit="mm", **kwargs) -> MeasurementType:
        return MeasurementType.objects.create(name=name, unit=unit, **kwargs)

    def create_observation(
        self, basin, measurement_type, timestamp=None, value=15.5, source="CSV_Ingest"
    ) -> Observation:
        if timestamp is None:
            count = Observation.objects.count()
            timestamp = timezone.now() + timezone.timedelta(seconds=count)
        return Observation.objects.create(
            basin=basin,
            measurement_type=measurement_type,
            timestamp=timestamp,
            value=value,
            source=source,
            created_by=self.user,
        )


class TestGetMeasurementTypesApi(BaseObservationApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("measurement-type-list")
        self.mtype1 = self.create_measurement_type(name="Precipitation", unit="mm")
        self.mtype2 = self.create_measurement_type(name="Temperature", unit="degC")

    def test_get_measurement_types_success(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data["data"])
        self.assertGreaterEqual(len(response.data["data"]["results"]), 2)

    def test_get_measurement_types_unauthenticated_fails(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_measurement_types(self):
        response = self.auth_client_inst.get(self.url, {"search": "Temp"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Temperature")

    def test_filter_by_name(self):
        response = self.auth_client_inst.get(self.url, {"name": "Precipitation"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["unit"], "mm")

    def test_filter_by_unit(self):
        response = self.auth_client_inst.get(self.url, {"unit": "degC"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Temperature")

    def test_filter_by_id(self):
        response = self.auth_client_inst.get(self.url, {"id": self.mtype1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.mtype1.id)


class TestCreateOrUpdateMeasurementTypeApi(BaseObservationApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("measurement-type-create-or-update")

    def test_create_measurement_type_success(self):
        response = self.auth_client_inst.post(
            self.url,
            {"name": "Water Level", "unit": "m"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["status"])
        self.assertEqual(response.data["message"], "Measurement type created successfully.")
        self.assertEqual(response.data["data"]["name"], "Water Level")

    def test_create_measurement_type_duplicate_name_fails(self):
        self.create_measurement_type(name="Humidity", unit="%")
        response = self.auth_client_inst.post(
            self.url,
            {"name": "Humidity", "unit": "%"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["status"])
        self.assertIn("name", response.data["errors"])

    def test_create_measurement_type_missing_fields_fails(self):
        response = self.auth_client_inst.post(
            self.url,
            {"unit": "mm"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_measurement_type_unauthenticated_fails(self):
        response = self.client.post(
            self.url,
            {"name": "Solar Radiation", "unit": "W/m2"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_measurement_type_success(self):
        mtype = self.create_measurement_type(name="Old Name", unit="mm")
        response = self.auth_client_inst.post(
            self.url,
            {"id": mtype.id, "name": "New Name", "unit": "cm"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertEqual(response.data["message"], "Measurement type updated successfully.")
        mtype.refresh_from_db()
        self.assertEqual(mtype.name, "New Name")
        self.assertEqual(mtype.unit, "cm")

    def test_update_measurement_type_nonexistent_returns_404(self):
        response = self.auth_client_inst.post(
            self.url,
            {"id": 99999, "name": "Ghost Type", "unit": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestDeleteMeasurementTypesApi(BaseObservationApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("measurement-type-delete")

    def test_delete_measurement_types_success(self):
        mt1 = self.create_measurement_type(name="Del1", unit="u1")
        mt2 = self.create_measurement_type(name="Del2", unit="u2")
        response = self.auth_client_inst.delete(
            self.url,
            {"ids": f"{mt1.id},{mt2.id}"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertFalse(MeasurementType.objects.filter(id__in=[mt1.id, mt2.id]).exists())

    def test_delete_measurement_types_list_format_success(self):
        mt1 = self.create_measurement_type(name="DelList1", unit="u1")
        response = self.auth_client_inst.delete(
            self.url,
            {"ids": [mt1.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(MeasurementType.objects.filter(id=mt1.id).exists())

    def test_delete_measurement_types_unauthenticated_fails(self):
        mt = self.create_measurement_type(name="NoAuthDel", unit="u")
        response = self.client.delete(self.url, {"ids": f"{mt.id}"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_measurement_types_missing_ids_fails(self):
        response = self.auth_client_inst.delete(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestGetObservationsApi(BaseObservationApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("observation-list")
        self.basin = self.create_basin(name="Observation Basin")
        self.mtype = self.create_measurement_type(name="Flow Rate", unit="m3/s")
        self.obs1 = self.create_observation(
            basin=self.basin,
            measurement_type=self.mtype,
            value=25.0,
            source="Sensor_A",
        )
        self.obs2 = self.create_observation(
            basin=self.basin,
            measurement_type=self.mtype,
            value=30.0,
            source="Sensor_B",
        )

    def test_get_observations_success(self):
        response = self.auth_client_inst.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data["data"])
        self.assertGreaterEqual(len(response.data["data"]["results"]), 2)

    def test_get_observations_unauthenticated_fails(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_observations(self):
        response = self.auth_client_inst.get(self.url, {"search": "Sensor_A"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "Sensor_A")

    def test_filter_observations_by_basin_id(self):
        response = self.auth_client_inst.get(self.url, {"basin_id": self.basin.basin_id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertGreaterEqual(len(results), 2)

    def test_filter_observations_by_measurement_type_id(self):
        response = self.auth_client_inst.get(self.url, {"measurement_type_id": self.mtype.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertGreaterEqual(len(results), 2)

    def test_filter_observations_by_id(self):
        response = self.auth_client_inst.get(self.url, {"id": self.obs1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.obs1.id)

    def test_filter_observations_by_value_thresholds(self):
        response = self.auth_client_inst.get(self.url, {"value_above": 26, "value_below": 30})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], self.obs2.id)


class TestCreateOrUpdateObservationApi(BaseObservationApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("observation-create-or-update")
        self.basin = self.create_basin(name="Creation Basin")
        self.mtype = self.create_measurement_type(name="Soil Moisture", unit="%")

    def test_create_observation_success(self):
        payload = {
            "basin_id": self.basin.id,
            "measurement_type_id": self.mtype.id,
            "timestamp": (timezone.now() + timezone.timedelta(hours=5)).isoformat(),
            "value": 42.5,
            "source": "Manual_Entry",
        }
        response = self.auth_client_inst.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["status"])
        self.assertEqual(response.data["message"], "Observation created successfully.")
        self.assertEqual(response.data["data"]["value"], 42.5)

    def test_create_observation_invalid_basin_id_fails(self):
        payload = {
            "basin_id": 99999,
            "measurement_type_id": self.mtype.id,
            "timestamp": timezone.now().isoformat(),
            "value": 10.0,
        }
        response = self.auth_client_inst.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["status"])

    def test_create_observation_invalid_measurement_type_id_fails(self):
        payload = {
            "basin_id": self.basin.id,
            "measurement_type_id": 99999,
            "timestamp": timezone.now().isoformat(),
            "value": 10.0,
        }
        response = self.auth_client_inst.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_observation_unauthenticated_fails(self):
        payload = {
            "basin_id": self.basin.id,
            "measurement_type_id": self.mtype.id,
            "timestamp": timezone.now().isoformat(),
            "value": 15.0,
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_observation_success(self):
        obs = self.create_observation(
            basin=self.basin,
            measurement_type=self.mtype,
            value=10.0,
        )
        payload = {
            "id": obs.id,
            "basin_id": self.basin.id,
            "measurement_type_id": self.mtype.id,
            "timestamp": obs.timestamp.isoformat(),
            "value": 99.9,
            "source": "Updated_Sensor",
        }
        response = self.auth_client_inst.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertEqual(response.data["message"], "Observation updated successfully.")
        obs.refresh_from_db()
        self.assertEqual(obs.value, 99.9)
        self.assertEqual(obs.source, "Updated_Sensor")

    def test_update_observation_nonexistent_returns_404(self):
        payload = {
            "id": 99999,
            "basin_id": self.basin.id,
            "measurement_type_id": self.mtype.id,
            "timestamp": timezone.now().isoformat(),
            "value": 20.0,
        }
        response = self.auth_client_inst.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestDeleteObservationsApi(BaseObservationApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("observation-delete")
        self.basin = self.create_basin(name="Delete Basin")
        self.mtype = self.create_measurement_type(name="DelType", unit="x")

    def test_delete_observations_success(self):
        obs1 = self.create_observation(basin=self.basin, measurement_type=self.mtype, value=1.0)
        obs2 = self.create_observation(basin=self.basin, measurement_type=self.mtype, value=2.0)
        response = self.auth_client_inst.delete(
            self.url,
            {"ids": f"{obs1.id},{obs2.id}"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertFalse(Observation.objects.filter(id__in=[obs1.id, obs2.id]).exists())

    def test_delete_observations_unauthenticated_fails(self):
        obs = self.create_observation(basin=self.basin, measurement_type=self.mtype, value=1.0)
        response = self.client.delete(self.url, {"ids": f"{obs.id}"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_observations_missing_ids_fails(self):
        response = self.auth_client_inst.delete(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestIngestObservationsCommand(SimpleTestCase):
    def test_handle_reports_success_for_each_file(self):
        stdout = io.StringIO()

        with patch(
            "apps.observations.management.commands.ingest_observations.Command._open_file",
            side_effect=lambda *args, **kwargs: io.BytesIO(b"csv"),
        ), patch(
            "apps.observations.management.commands.ingest_observations.IngestionService.ingest_rainfall",
            return_value=None,
        ), patch(
            "apps.observations.management.commands.ingest_observations.IngestionService.ingest_temperature",
            return_value=None,
        ):
            call_command(
                "ingest_observations",
                rainfall="rain.csv",
                temperature="temp.csv",
                stdout=stdout,
            )

        output = stdout.getvalue()
        self.assertIn("Ingesting rainfall", output)
        self.assertIn("Ingesting temperature", output)
        self.assertIn("Successfully created.", output)
