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

LOGIN_URL = "/api/account/login/"
ME_URL = "/api/account/"
LOCALE_URL = "/api/account/locale/"


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
    """POST /api/account/login/

    Authorization 헤더가 있으면 공용 FirebaseAuthentication(accounts.authentication의
    verify_id_token)도 먼저 실행된다. LoginView.post()가 직접 부르는
    accounts.views.verify_id_token만 mocking하면 실제 Firebase 서버에 접속하려다
    실패해서(InvalidFirebaseToken) 뷰 로직까지 가지 못하고 401이 먼저 난다.
    그래서 헤더를 보내는 테스트는 두 위치 모두 mocking한다.
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    @patch("accounts.authentication.verify_id_token")
    @patch("accounts.views.verify_id_token")
    def test_google_login_creates_new_member(self, mock_verify, mock_verify_auth):
        decoded = make_decoded_token("google-uid-1", provider="google.com")
        mock_verify.return_value = decoded
        mock_verify_auth.return_value = decoded

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member = Member.objects.get(firebase_uid="google-uid-1")
        self.assertEqual(member.provider, Member.Provider.GOOGLE)
        self.assertIsNotNone(member.agreed_terms_at)

    @patch("accounts.authentication.verify_id_token")
    @patch("accounts.views.verify_id_token")
    def test_apple_login_creates_new_member(self, mock_verify, mock_verify_auth):
        decoded = make_decoded_token("apple-uid-1", provider="apple.com")
        mock_verify.return_value = decoded
        mock_verify_auth.return_value = decoded

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member = Member.objects.get(firebase_uid="apple-uid-1")
        self.assertEqual(member.provider, Member.Provider.APPLE)

    @patch("accounts.authentication.verify_id_token")
    @patch("accounts.views.verify_id_token")
    def test_same_account_login_again_does_not_duplicate(self, mock_verify, mock_verify_auth):
        decoded = make_decoded_token("google-uid-2", provider="google.com")
        mock_verify.return_value = decoded
        mock_verify_auth.return_value = decoded

        first = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)
        second = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Member.objects.filter(firebase_uid="google-uid-2").count(), 1)
        self.assertEqual(first.data["id"], second.data["id"])

    @patch("accounts.authentication.verify_id_token")
    @patch("accounts.views.verify_id_token")
    def test_new_member_without_terms_agreement_is_rejected(self, mock_verify, mock_verify_auth):
        decoded = make_decoded_token("google-uid-3")
        mock_verify.return_value = decoded
        mock_verify_auth.return_value = decoded

        response = self.client.post(LOGIN_URL, {}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Member.objects.filter(firebase_uid="google-uid-3").exists())

    @patch("accounts.authentication.verify_id_token")
    @patch("accounts.views.verify_id_token")
    def test_unsupported_sign_in_provider_is_rejected(self, mock_verify, mock_verify_auth):
        decoded = make_decoded_token("uid-4", provider="password")
        mock_verify.return_value = decoded
        mock_verify_auth.return_value = decoded

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
    """GET /api/account/"""

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


class LocaleViewTests(TestCase):
    """PATCH /api/account/locale/

    로그인 여부와 상관없이 호출할 수 있다. 로그인했으면 실제로 저장하고,
    로그인 안 했으면 값 검증만 하고 응답만 돌려준다 (DETAIL_SPEC 6-1 #9).
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    def test_anonymous_user_gets_response_but_nothing_saved(self):
        response = self.client.patch(
            LOCALE_URL, {"nationality": "KR", "language": "ko"}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 응답에는 language만 있어야 한다 (nationality는 응답에 없음).
        self.assertEqual(response.data, {"language": "ko"})
        # 저장할 회원이 없으므로 DB에 회원이 하나도 생기지 않아야 한다.
        self.assertEqual(Member.objects.count(), 0)

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_locale_is_saved(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="locale-uid-1",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("locale-uid-1")

        response = self.client.patch(
            LOCALE_URL, {"nationality": "US", "language": "en"}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": "en"})
        member.refresh_from_db()
        self.assertEqual(member.nationality, "US")
        self.assertEqual(member.language, "en")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_only_changes_own_locale(self, mock_verify):
        me = Member.objects.create(
            firebase_uid="locale-uid-me",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
            nationality="KR",
            language="ko",
        )
        other = Member.objects.create(
            firebase_uid="locale-uid-other",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
            nationality="JP",
            language="ja",
        )
        mock_verify.return_value = make_decoded_token("locale-uid-me")

        response = self.client.patch(
            LOCALE_URL, {"nationality": "US", "language": "en"}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        me.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(me.nationality, "US")
        self.assertEqual(me.language, "en")
        # 다른 회원은 그대로여야 한다.
        self.assertEqual(other.nationality, "JP")
        self.assertEqual(other.language, "ja")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_empty_string_is_accepted(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="locale-uid-empty",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
            nationality="KR",
            language="ko",
        )
        mock_verify.return_value = make_decoded_token("locale-uid-empty")

        response = self.client.patch(
            LOCALE_URL, {"nationality": "", "language": ""}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": ""})
        member.refresh_from_db()
        self.assertEqual(member.nationality, "")
        self.assertEqual(member.language, "")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_null_is_accepted(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="locale-uid-null",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
            nationality="KR",
            language="ko",
        )
        mock_verify.return_value = make_decoded_token("locale-uid-null")

        response = self.client.patch(
            LOCALE_URL, {"nationality": None, "language": None}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": None})
        member.refresh_from_db()
        self.assertIsNone(member.nationality)
        self.assertIsNone(member.language)

    def test_anonymous_user_empty_string_is_accepted(self):
        response = self.client.patch(
            LOCALE_URL, {"nationality": "", "language": ""}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": ""})
        self.assertEqual(Member.objects.count(), 0)

    def test_anonymous_user_null_is_accepted(self):
        response = self.client.patch(
            LOCALE_URL, {"nationality": None, "language": None}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": None})
        self.assertEqual(Member.objects.count(), 0)


class MePatchIsGoneTests(TestCase):
    """PATCH /api/account/는 이제 없다. GET만 지원해야 한다.

    MeView는 permission_classes=[IsAuthenticated]라서, 로그인 여부 확인이
    "이 메서드가 있는지" 확인보다 먼저 실행된다(DRF dispatch 순서). 그래서
    - 로그인 안 한 상태로 PATCH를 보내면 (메서드가 없어도) 401이 먼저 난다.
    - 로그인한 상태로 PATCH를 보내야 비로소 진짜 405를 볼 수 있다.
    둘 다 확인해야 "PATCH가 없어졌다"는 사실을 제대로 검증한 것이다.
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    def test_patch_me_without_login_is_rejected_by_permission_first(self):
        response = self.client.patch(
            ME_URL, {"nationality": "KR", "language": "ko"}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_patch_me_with_login_is_no_longer_allowed(self, mock_verify):
        Member.objects.create(
            firebase_uid="me-patch-gone-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("me-patch-gone-uid")

        response = self.client.patch(
            ME_URL, {"nationality": "KR", "language": "ko"}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
