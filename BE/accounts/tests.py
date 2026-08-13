"""
로그인(Phase 1) 완료 기준 체크리스트를 검증하는 테스트.

실제 Firebase 서버에 접속하지 않는다. accounts.firebase.verify_id_token이
반환할 decoded token 값을 mocking해서, "Firebase가 이 사람이 맞다고 확인해줬다"는
상황을 흉내낸다.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.firebase import InvalidFirebaseToken
from accounts.models import Member

LOGIN_URL = "/api/auth/login/"
ME_URL = "/api/auth/me/"


def make_decoded_token(uid, provider="google.com", email="test@example.com",
                        name="테스터", picture="http://example.com/pic.jpg"):
    return {
        "uid": uid,
        "email": email,
        "name": name,
        "picture": picture,
        "firebase": {"sign_in_provider": provider},
    }


class LoginViewTests(TestCase):
    """POST /api/auth/login/

    LoginView는 토큰 검증을 직접 하고, 공용 FirebaseAuthentication은 타지 않는다
    (accounts/views.py의 LoginView 설명 참고). 그래서 accounts.views.verify_id_token만
    mocking하면 된다.
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    @patch("accounts.views.verify_id_token")
    def test_google_login_creates_new_member(self, mock_verify):
        mock_verify.return_value = make_decoded_token("google-uid-1", provider="google.com")

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member = Member.objects.get(firebase_uid="google-uid-1")
        self.assertEqual(member.provider, Member.Provider.GOOGLE)
        self.assertIsNotNone(member.agreed_terms_at)

    @patch("accounts.views.verify_id_token")
    def test_apple_login_creates_new_member(self, mock_verify):
        mock_verify.return_value = make_decoded_token("apple-uid-1", provider="apple.com")

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member = Member.objects.get(firebase_uid="apple-uid-1")
        self.assertEqual(member.provider, Member.Provider.APPLE)

    @patch("accounts.views.verify_id_token")
    def test_same_account_login_again_does_not_duplicate(self, mock_verify):
        mock_verify.return_value = make_decoded_token("google-uid-2", provider="google.com")

        first = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)
        second = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Member.objects.filter(firebase_uid="google-uid-2").count(), 1)
        self.assertEqual(first.data["id"], second.data["id"])

    @patch("accounts.views.verify_id_token")
    def test_new_member_without_terms_agreement_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("google-uid-3")

        response = self.client.post(LOGIN_URL, {}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Member.objects.filter(firebase_uid="google-uid-3").exists())

    @patch("accounts.views.verify_id_token")
    def test_unsupported_sign_in_provider_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("uid-4", provider="password")

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "지원하지 않는 로그인 방식입니다")
        self.assertFalse(Member.objects.filter(firebase_uid="uid-4").exists())

    @patch("accounts.views.verify_id_token")
    def test_invalid_token_is_rejected(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "다시 로그인하세요")

    def test_login_without_token_is_rejected(self):
        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "다시 로그인하세요")

    def test_no_email_password_signup_path_exists(self):
        """이메일·비밀번호로 가입하는 API 자체가 없어야 한다."""
        response = self.client.post(
            LOGIN_URL, {"email": "a@a.com", "password": "1234", "agree_terms": True}, format="json",
        )
        # 토큰이 없으므로 이메일/비밀번호를 보내도 그냥 인증 실패로 처리된다.
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeViewTests(TestCase):
    """GET /api/auth/me/"""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    def test_me_without_login_is_rejected(self):
        response = self.client.get(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    @patch("accounts.authentication.verify_id_token")
    def test_me_with_invalid_token_is_rejected(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "다시 로그인하세요")

    @patch("accounts.authentication.verify_id_token")
    def test_me_with_valid_token_but_unknown_member_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("unknown-uid")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    @patch("accounts.authentication.verify_id_token")
    def test_me_returns_logged_in_member(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="google-uid-5",
            provider=Member.Provider.GOOGLE,
            email="member@example.com",
            nickname="회원",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("google-uid-5")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], member.id)
        self.assertEqual(response.data["email"], "member@example.com")


class MemberModelTests(TestCase):
    """회원 정보 보관 항목이 준비되어 있는지 확인한다."""

    def test_member_has_reserved_fields_for_future_phases(self):
        member = Member.objects.create(
            firebase_uid="uid-reserved",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )

        self.assertIsNone(member.nationality)
        self.assertIsNone(member.language)
        self.assertFalse(member.is_withdrawn)
        self.assertIsNone(member.withdrawn_at)

    def test_member_has_no_phone_number_field(self):
        field_names = [f.name for f in Member._meta.get_fields()]
        self.assertNotIn("phone", field_names)
        self.assertNotIn("phone_number", field_names)
