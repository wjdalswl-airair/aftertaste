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
    def test_long_social_name_is_truncated_to_nickname_max_length(self, mock_verify, mock_verify_auth):
        """소셜에서 받은 이름이 20자를 넘으면 잘라서 저장한다 (그대로 넣으면 가입 실패)."""
        long_name = "가" * 50
        decoded = make_decoded_token("google-uid-longname", name=long_name)
        mock_verify.return_value = decoded
        mock_verify_auth.return_value = decoded

        response = self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member = Member.objects.get(firebase_uid="google-uid-longname")
        self.assertEqual(member.nickname, "가" * 20)

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


class MeProfileSummaryTests(TestCase):
    """GET /api/account/ 프로필 응답의 활동 요약 (DETAIL_SPEC 3-1, 6-1 #22).

    - reviewed_places_count: 내가 리뷰를 쓴 서로 다른 명소 수 (감춰진 리뷰 제외)
    - created_courses_count: 내가 만든 코스 수
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = Member.objects.create(
            firebase_uid="summary-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )

    @patch("accounts.authentication.verify_id_token")
    def test_counts_are_zero_for_new_member(self, mock_verify):
        mock_verify.return_value = make_decoded_token("summary-uid")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reviewed_places_count"], 0)
        self.assertEqual(response.data["created_courses_count"], 0)

    @patch("accounts.authentication.verify_id_token")
    def test_reviewed_places_count_dedupes_by_place_and_excludes_hidden(self, mock_verify):
        from courses.models import Course
        from places.models import Place
        from reviews.models import Review

        mock_verify.return_value = make_decoded_token("summary-uid")
        place_a = Place.objects.create(name="경복궁")
        place_b = Place.objects.create(name="남산타워")

        # 같은 명소에 리뷰 2개 → 1로 센다
        Review.objects.create(member=self.member, place=place_a, rating=5, content="1", language="ko")
        Review.objects.create(member=self.member, place=place_a, rating=4, content="2", language="ko")
        Review.objects.create(member=self.member, place=place_b, rating=3, content="3", language="ko")
        # 감춰진 리뷰만 있는 명소는 안 센다
        place_c = Place.objects.create(name="숨겨진명소")
        Review.objects.create(
            member=self.member, place=place_c, rating=1, content="4", language="ko", is_hidden=True
        )
        Course.objects.create(place=place_a, creator=self.member, title="내 코스 1")
        Course.objects.create(place=place_b, creator=self.member, title="내 코스 2")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reviewed_places_count"], 2)
        self.assertEqual(response.data["created_courses_count"], 2)

    @patch("accounts.authentication.verify_id_token")
    def test_other_members_activity_does_not_count(self, mock_verify):
        from places.models import Place
        from reviews.models import Review

        mock_verify.return_value = make_decoded_token("summary-uid")
        other = Member.objects.create(
            firebase_uid="other-summary-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        place = Place.objects.create(name="경복궁")
        Review.objects.create(member=other, place=place, rating=5, content="남의 리뷰", language="ko")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.data["reviewed_places_count"], 0)


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

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_is_treated_as_anonymous(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.patch(
            LOCALE_URL, {"nationality": "KR", "language": "ko"}, format="json",
            **self.auth_header,
        )

        # 무효/만료 토큰이어도 401이 아니라 비로그인과 동일하게 200을 받아야 한다.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": "ko"})
        # 저장할 회원을 특정할 수 없으므로 DB에는 아무것도 남지 않아야 한다.
        self.assertEqual(Member.objects.count(), 0)


class MeNicknamePatchTests(TestCase):
    """PATCH /api/account/ - 마이페이지 닉네임 수정 (Phase 3 사이클 C).

    2026-08-17에는 "PATCH /account에서 국적·언어를 다루지 않는다"는 결정으로
    PATCH 자체를 없앴었다(예전 MePatchIsGoneTests, DETAIL_SPEC 6-1 #9). 이번 사이클에서
    "닉네임 수정"용 PATCH가 다시 생겼으므로, 예전 테스트의 "PATCH는 405"라는 전제가
    깨졌다. 그렇다고 그 테스트가 지키려던 의도(국적·언어는 이 엔드포인트로 못 바꾼다)까지
    버리면 안 되므로, "닉네임은 바뀌지만 국적·언어는 무시된다"로 다시 검증한다.
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    def test_patch_me_without_login_is_rejected(self):
        response = self.client.patch(
            ME_URL, {"nickname": "새이름"}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_patch_me_with_invalid_token_is_rejected(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.patch(
            ME_URL, {"nickname": "새이름"}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_can_change_nickname(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="nickname-patch-uid",
            provider=Member.Provider.GOOGLE,
            nickname="원래이름",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("nickname-patch-uid")

        response = self.client.patch(
            ME_URL, {"nickname": "새이름"}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        member.refresh_from_db()
        self.assertEqual(member.nickname, "새이름")

    @patch("accounts.authentication.verify_id_token")
    def test_nickname_at_max_length_is_accepted(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="nickname-maxlen-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("nickname-maxlen-uid")
        exactly_max = "가" * 20  # 닉네임 최대 길이 (DETAIL_SPEC 6-1 #21)

        response = self.client.patch(
            ME_URL, {"nickname": exactly_max}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        member.refresh_from_db()
        self.assertEqual(member.nickname, exactly_max)

    @patch("accounts.authentication.verify_id_token")
    def test_nickname_over_max_length_is_rejected_with_400_not_db_error(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="nickname-toolong-uid",
            provider=Member.Provider.GOOGLE,
            nickname="원래이름",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("nickname-toolong-uid")
        too_long = "가" * 21  # 닉네임 최대 길이(20자)를 넘김

        response = self.client.patch(
            ME_URL, {"nickname": too_long}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        member.refresh_from_db()
        self.assertEqual(member.nickname, "원래이름")

    @patch("accounts.authentication.verify_id_token")
    def test_nationality_and_language_in_body_are_ignored(self, mock_verify):
        """PATCH /account/ body에 국적/언어를 보내도 반영되지 않는다 (LocaleView와 책임 분리).

        DETAIL_SPEC 6-1 #9: 국적/언어는 PATCH /account/locale/(LocaleView)의 책임이다.
        """
        member = Member.objects.create(
            firebase_uid="nickname-ignore-locale-uid",
            provider=Member.Provider.GOOGLE,
            nickname="원래이름",
            nationality="KR",
            language="ko",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("nickname-ignore-locale-uid")

        response = self.client.patch(
            ME_URL,
            {"nickname": "새이름", "nationality": "US", "language": "en"},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        member.refresh_from_db()
        self.assertEqual(member.nickname, "새이름")
        self.assertEqual(member.nationality, "KR")
        self.assertEqual(member.language, "ko")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_can_change_profile_image_url(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="profile-img-uid",
            provider=Member.Provider.GOOGLE,
            profile_image_url="https://old.example.com/a.jpg",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("profile-img-uid")

        response = self.client.patch(
            ME_URL,
            {"profile_image_url": "https://storage.example.com/new.jpg"},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        member.refresh_from_db()
        self.assertEqual(member.profile_image_url, "https://storage.example.com/new.jpg")

    @patch("accounts.authentication.verify_id_token")
    def test_blank_profile_image_url_clears_it(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="profile-img-clear-uid",
            provider=Member.Provider.APPLE,
            profile_image_url="https://old.example.com/a.jpg",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("profile-img-clear-uid")

        response = self.client.patch(
            ME_URL, {"profile_image_url": ""}, format="json", **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        member.refresh_from_db()
        self.assertIsNone(member.profile_image_url)

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_profile_image_url_is_rejected_with_400(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="profile-img-bad-uid",
            provider=Member.Provider.GOOGLE,
            profile_image_url="https://old.example.com/a.jpg",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("profile-img-bad-uid")

        response = self.client.patch(
            ME_URL, {"profile_image_url": "그냥 텍스트"}, format="json", **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        member.refresh_from_db()
        self.assertEqual(member.profile_image_url, "https://old.example.com/a.jpg")

    @patch("accounts.authentication.verify_id_token")
    def test_patch_only_nickname_leaves_profile_image_untouched(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="profile-img-partial-uid",
            provider=Member.Provider.GOOGLE,
            nickname="원래이름",
            profile_image_url="https://keep.example.com/a.jpg",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("profile-img-partial-uid")

        response = self.client.patch(
            ME_URL, {"nickname": "새이름"}, format="json", **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        member.refresh_from_db()
        self.assertEqual(member.nickname, "새이름")
        self.assertEqual(member.profile_image_url, "https://keep.example.com/a.jpg")


class MeGetRegressionTests(TestCase):
    """GET /api/account/, /api/account/favorites/, /api/account/reviews/, LocaleView가
    닉네임 PATCH 추가로 회귀 없이 그대로 동작하는지 확인한다."""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    @patch("accounts.authentication.verify_id_token")
    def test_get_me_still_works(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="regression-get-uid",
            provider=Member.Provider.GOOGLE,
            email="regression@example.com",
            nickname="회원",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("regression-get-uid")

        response = self.client.get(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], member.id)

    @patch("accounts.authentication.verify_id_token")
    def test_get_my_favorites_still_works(self, mock_verify):
        Member.objects.create(
            firebase_uid="regression-fav-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("regression-fav-uid")

        response = self.client.get("/api/account/favorites/", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("favorites", response.data)

    @patch("accounts.authentication.verify_id_token")
    def test_get_my_reviews_still_works(self, mock_verify):
        Member.objects.create(
            firebase_uid="regression-review-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("regression-review-uid")

        response = self.client.get("/api/account/reviews/", **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("reviews", response.data)

    def test_locale_view_still_works_for_anonymous(self):
        response = self.client.patch(
            LOCALE_URL, {"nationality": "KR", "language": "ko"}, format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"language": "ko"})

    @patch("accounts.authentication.verify_id_token")
    def test_locale_view_still_works_for_logged_in_member(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="regression-locale-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("regression-locale-uid")

        response = self.client.patch(
            LOCALE_URL, {"nationality": "JP", "language": "ja"}, format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        member.refresh_from_db()
        self.assertEqual(member.nationality, "JP")
        self.assertEqual(member.language, "ja")


class WithdrawalTests(TestCase):
    """DELETE /api/account/ - 회원 탈퇴 (Phase 3 사이클 C).

    DETAIL_SPEC 2-1 "탈퇴 처리가 특이합니다", 3-1 회원 예외 상황 표를 근거로 만들었다.
    """

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

    def test_withdraw_without_login_is_rejected(self):
        response = self.client.delete(ME_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_withdraw_with_invalid_token_is_rejected(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.delete(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_can_withdraw(self, mock_verify):
        Member.objects.create(
            firebase_uid="withdraw-uid-1",
            provider=Member.Provider.GOOGLE,
            email="withdraw1@example.com",
            nickname="탈퇴할사람",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("withdraw-uid-1")

        response = self.client.delete(ME_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("accounts.authentication.verify_id_token")
    def test_member_row_is_not_physically_deleted(self, mock_verify):
        Member.objects.create(
            firebase_uid="withdraw-uid-2",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("withdraw-uid-2")
        count_before = Member.objects.count()

        self.client.delete(ME_URL, **self.auth_header)

        self.assertEqual(Member.objects.count(), count_before)

    @patch("accounts.authentication.verify_id_token")
    def test_personal_info_is_cleared_on_withdraw(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="withdraw-uid-3",
            provider=Member.Provider.GOOGLE,
            email="withdraw3@example.com",
            nickname="탈퇴할사람",
            profile_image_url="http://example.com/pic.jpg",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("withdraw-uid-3")

        self.client.delete(ME_URL, **self.auth_header)

        member.refresh_from_db()
        self.assertIsNone(member.nickname)
        self.assertIsNone(member.email)
        self.assertIsNone(member.profile_image_url)

    @patch("accounts.authentication.verify_id_token")
    def test_is_withdrawn_and_withdrawn_at_are_set(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="withdraw-uid-4",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("withdraw-uid-4")

        self.client.delete(ME_URL, **self.auth_header)

        member.refresh_from_db()
        self.assertTrue(member.is_withdrawn)
        self.assertIsNotNone(member.withdrawn_at)

    @patch("accounts.authentication.verify_id_token")
    def test_withdrawn_member_cannot_login_again_gets_new_member(self, mock_verify):
        """같은 firebase_uid로 재로그인하면 옛 계정이 아니라 완전히 새로운 Member가 생겨야 한다."""
        old_member = Member.objects.create(
            firebase_uid="withdraw-relogin-uid",
            provider=Member.Provider.GOOGLE,
            email="relogin@example.com",
            nickname="탈퇴할사람",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        old_id = old_member.id
        mock_verify.return_value = make_decoded_token("withdraw-relogin-uid")

        self.client.delete(ME_URL, **self.auth_header)
        self.assertEqual(Member.objects.count(), 1)

        with patch("accounts.views.verify_id_token") as mock_verify_login:
            decoded = make_decoded_token("withdraw-relogin-uid")
            mock_verify_login.return_value = decoded
            response = self.client.post(
                LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header,
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Member.objects.count(), 2)
        new_id = response.data["id"]
        self.assertNotEqual(new_id, old_id)

    @patch("accounts.authentication.verify_id_token")
    def test_favorites_and_reviews_survive_withdrawal(self, mock_verify):
        from favorites.models import Favorite
        from reviews.models import Review
        from places.models import Place

        member = Member.objects.create(
            firebase_uid="withdraw-fk-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        place = Place.objects.create(name="경복궁", address="서울시 종로구")
        favorite = Favorite.objects.create(member=member, place=place)
        review = Review.objects.create(
            member=member, place=place, rating=5, content="좋아요", language="ko",
        )
        mock_verify.return_value = make_decoded_token("withdraw-fk-uid")

        self.client.delete(ME_URL, **self.auth_header)

        self.assertTrue(Favorite.objects.filter(pk=favorite.pk).exists())
        self.assertTrue(Review.objects.filter(pk=review.pk).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_withdrawn_member_review_shows_as_withdrawn_user(self, mock_verify):
        from places.models import Place
        from reviews.models import Review

        member = Member.objects.create(
            firebase_uid="withdraw-review-author-uid",
            provider=Member.Provider.GOOGLE,
            nickname="탈퇴할작성자",
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        place = Place.objects.create(name="경복궁", address="서울시 종로구")
        Review.objects.create(
            member=member, place=place, rating=5, content="좋아요", language="ko",
        )
        mock_verify.return_value = make_decoded_token("withdraw-review-author-uid")

        self.client.delete(ME_URL, **self.auth_header)

        response = self.client.get(f"/api/places/{place.id}/reviews/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reviews"][0]["author_nickname"], "탈퇴한 사용자")

    def test_new_member_after_relogin_cannot_see_old_favorites_or_reviews(self):
        from favorites.models import Favorite
        from places.models import Place
        from reviews.models import Review

        old_member = Member.objects.create(
            firebase_uid="withdraw-newmember-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        place = Place.objects.create(name="경복궁", address="서울시 종로구")
        Favorite.objects.create(member=old_member, place=place)
        Review.objects.create(
            member=old_member, place=place, rating=5, content="좋아요", language="ko",
        )

        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("withdraw-newmember-uid")
            self.client.delete(ME_URL, **self.auth_header)

        with patch("accounts.views.verify_id_token") as mock_verify_login, patch("accounts.authentication.verify_id_token") as mock_verify_auth:
            decoded = make_decoded_token("withdraw-newmember-uid")
            mock_verify_login.return_value = decoded
            mock_verify_auth.return_value = decoded
            self.client.post(LOGIN_URL, {"agree_terms": True}, format="json", **self.auth_header)

        with patch("accounts.authentication.verify_id_token") as mock_verify_new:
            mock_verify_new.return_value = make_decoded_token("withdraw-newmember-uid")
            fav_response = self.client.get("/api/account/favorites/", **self.auth_header)
            review_response = self.client.get("/api/account/reviews/", **self.auth_header)

        self.assertEqual(fav_response.status_code, status.HTTP_200_OK)
        self.assertEqual(fav_response.data["favorites"], [])
        self.assertEqual(review_response.status_code, status.HTTP_200_OK)
        self.assertEqual(review_response.data["reviews"], [])

    @patch("accounts.authentication.verify_id_token")
    def test_token_no_longer_works_after_withdrawal(self, mock_verify):
        """탈퇴 후 같은 토큰으로 다른 API(GET /api/account/)를 호출하면 401이어야 한다.

        FirebaseAuthentication.authenticate()는 is_withdrawn을 직접 확인하지 않지만,
        DELETE 처리에서 firebase_uid를 "withdrawn:<uuid>"로 바꿔버리므로, 토큰이 담고 있는
        원래 firebase_uid로는 더 이상 어떤 Member도 조회되지 않는다. 그 결과 인증이
        AnonymousUser로 떨어지고, IsAuthenticated가 401로 막는다.
        """
        mock_verify.return_value = make_decoded_token("withdraw-token-reuse-uid")
        Member.objects.create(
            firebase_uid="withdraw-token-reuse-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )

        delete_response = self.client.delete(ME_URL, **self.auth_header)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        get_response = self.client.get(ME_URL, **self.auth_header)
        self.assertEqual(get_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_withdrawing_again_with_same_token_is_blocked_by_auth_not_by_view(self, mock_verify):
        """이미 탈퇴한 사람이 같은 토큰으로 탈퇴를 다시 시도하면, DELETE 로직에 도달하기도
        전에 인증 단계에서 401로 막힌다 (토큰의 firebase_uid로 더 이상 회원을 못 찾으므로)."""
        mock_verify.return_value = make_decoded_token("withdraw-again-uid")
        Member.objects.create(
            firebase_uid="withdraw-again-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )

        first = self.client.delete(ME_URL, **self.auth_header)
        self.assertEqual(first.status_code, status.HTTP_204_NO_CONTENT)

        second = self.client.delete(ME_URL, **self.auth_header)
        self.assertEqual(second.status_code, status.HTTP_401_UNAUTHORIZED)
