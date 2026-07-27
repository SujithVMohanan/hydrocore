from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Users


class BaseUserApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def make_user(self, email="test@example.com", password="Test@1234", **kwargs) -> Users:
        return Users.objects.create_user(email=email, password=password, **kwargs)

    def make_admin(self, email="admin@example.com", password="Admin@1234") -> Users:
        return Users.objects.create_superuser(email=email, password=password)

    def auth_client(self, user: Users) -> APIClient:
        client = APIClient()
        token = str(RefreshToken.for_user(user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client


class TestRegisterApi(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("user-register")

    def test_register_success(self):
        response = self.client.post(
            self.url,
            {"email": "newreg@example.com", "password": "Reg@12345"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["status"])
        self.assertIn("token", response.data["data"])

    def test_register_duplicate_email_fails(self):
        self.make_user(email="dup@example.com")
        response = self.client.post(
            self.url,
            {"email": "dup@example.com", "password": "Dup@1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["status"])

    def test_register_missing_email_fails(self):
        response = self.client.post(self.url, {"password": "Test@1234"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password_fails(self):
        response = self.client.post(
            self.url,
            {"email": "short@example.com", "password": "123"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestLoginApi(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("user-login")
        self.user = self.make_user(email="login@example.com", password="Login@1234")

    def test_login_success_returns_tokens(self):
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": "Login@1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data["data"])
        self.assertIn("refresh_token", response.data["data"])

    def test_login_wrong_password_fails(self):
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": "WrongPass"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_nonexistent_user_fails(self):
        response = self.client.post(
            self.url,
            {"email": "ghost@example.com", "password": "Ghost@1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user_fails(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.url,
            {"email": "login@example.com", "password": "Login@1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestLogoutApi(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("user-logout")
        self.user = self.make_user(email="logout@example.com", password="Logout@1234")
        self.refresh = RefreshToken.for_user(self.user)
        self.access = str(self.refresh.access_token)
        self.refresh_str = str(self.refresh)
        self.auth_client_inst = APIClient()
        self.auth_client_inst.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

    def test_logout_success_expires_access_token(self):
        response = self.auth_client_inst.post(
            self.url,
            {"refresh_token": self.refresh_str},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["status"])
        self.assertIn("expired", response.data["message"].lower())

        # Same access token must no longer work on protected APIs
        protected = reverse("user-list")
        after = self.auth_client_inst.get(protected)
        self.assertEqual(after.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_unauthenticated_fails(self):
        response = self.client.post(
            self.url,
            {"refresh_token": self.refresh_str},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_missing_refresh_token_fails(self):
        response = self.auth_client_inst.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["status"])

    def test_logout_invalid_refresh_token_fails(self):
        response = self.auth_client_inst.post(
            self.url,
            {"refresh_token": "not-a-valid-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["status"])

    def test_logout_twice_with_same_refresh_fails(self):
        first = self.auth_client_inst.post(
            self.url,
            {"refresh_token": self.refresh_str},
            format="json",
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        # Need a fresh access token to call logout again (old one is blacklisted)
        new_refresh = RefreshToken.for_user(self.user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(new_refresh.access_token)}")
        second = client.post(
            self.url,
            {"refresh_token": self.refresh_str},
            format="json",
        )
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)


class TestGetUsersApi(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user(email="getadmin@example.com")
        self.client = self.auth_client(self.admin)
        self.url = reverse("user-list")
        self.make_user(email="alpha@example.com", full_name="Alpha User")
        self.make_user(email="beta@example.com", full_name="Beta User")

    def test_get_users_returns_list(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_users_requires_auth(self):
        response = APIClient().get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_search_by_name(self):
        response = self.client.get(self.url, {"search": "Alpha"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_by_email(self):
        response = self.client.get(self.url, {"search": "beta@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_user_id(self):
        user = self.make_user(email="specific@example.com")
        response = self.client.get(self.url, {"user_id": user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestCreateOrUpdateUserApi(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user(email="cou_admin@example.com")
        self.client = self.auth_client(self.admin)
        self.url = reverse("user-create-or-update")

    def test_create_user_success(self):
        response = self.client.post(
            self.url,
            {"email": "create1@example.com", "password": "Create@1234", "full_name": "Created User"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "User created successfully.")

    def test_create_user_duplicate_email_fails(self):
        self.make_user(email="exists@example.com")
        response = self.client.post(
            self.url,
            {"email": "exists@example.com", "password": "Exists@1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_requires_auth(self):
        response = APIClient().post(
            self.url,
            {"email": "noauth@example.com", "password": "Test@1234"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_user_full_name(self):
        target = self.make_user(email="target@example.com", full_name="Old")
        response = self.client.post(
            self.url,
            {"user_id": target.id, "full_name": "Updated Name"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "User updated successfully.")
        target.refresh_from_db()
        self.assertEqual(target.full_name, "Updated Name")

    def test_update_nonexistent_user_returns_404(self):
        response = self.client.post(
            self.url,
            {"user_id": 99999, "full_name": "Ghost"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_email_uniqueness_check_excludes_self(self):
        target = self.make_user(email="self@example.com")
        response = self.client.post(
            self.url,
            {"user_id": target.id, "email": "self@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_email_taken_by_another_user_fails(self):
        self.make_user(email="taken@example.com")
        target = self.make_user(email="mine@example.com")
        response = self.client.post(
            self.url,
            {"user_id": target.id, "email": "taken@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestDeleteUsersApi(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.admin = self.make_user(email="del_admin@example.com")
        self.client = self.auth_client(self.admin)
        self.url = reverse("user-delete")

    def test_delete_users_success(self):
        user_one = self.make_user(email="todel1@example.com")
        user_two = self.make_user(email="todel2@example.com")
        response = self.client.delete(
            self.url,
            {"user_ids": [user_one.id, user_two.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Users.objects.filter(id__in=[user_one.id, user_two.id]).exists())

    def test_delete_requires_auth(self):
        user = self.make_user(email="noauth_del@example.com")
        response = APIClient().delete(self.url, {"user_ids": [user.id]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_missing_user_ids_fails(self):
        response = self.client.delete(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_does_not_remove_superuser(self):
        admin = self.make_admin(email="nodelete_admin@example.com")
        self.client.delete(self.url, {"user_ids": [admin.id]}, format="json")
        self.assertTrue(Users.objects.filter(id=admin.id).exists())


class TestDashboardView(BaseUserApiTest):
    def setUp(self):
        super().setUp()
        self.url = reverse("user-dashboard")

    def test_dashboard_ajax_all_filter_returns_success(self):
        response = self.client.get(
            self.url,
            {"ajax": "1", "basin_id": "all"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["data"], {})
