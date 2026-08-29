"""Phase 3 "사이클 A" 즐겨찾기 체크리스트를 검증하는 테스트.

DETAIL_SPEC.md 2-4, 3-4 / PHASES/PHASE3.md 1번(즐겨찾기) 완료 기준 체크리스트를 근거로 만들었다.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.firebase import InvalidFirebaseToken
from accounts.models import Member
from favorites.models import Favorite
from places.models import Place

MY_FAVORITES_URL = "/api/account/favorites/"


def favorite_url(place_id):
    return f"/api/places/{place_id}/favorite/"


def place_detail_url(place_id):
    return f"/api/places/{place_id}/"


def make_decoded_token(uid):
    return {
        "uid": uid,
        "email": f"{uid}@example.com",
        "name": "테스터",
        "picture": "http://example.com/pic.jpg",
        "firebase": {"sign_in_provider": "google.com"},
    }


def create_member(uid="fav-uid-1"):
    return Member.objects.create(
        firebase_uid=uid,
        provider=Member.Provider.GOOGLE,
        nickname="회원",
        agreed_terms_at="2026-01-01T00:00:00Z",
    )


class FavoriteChecklistTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = create_member("fav-uid-1")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_user_can_save_place(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")

        response = self.client.post(favorite_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Favorite.objects.filter(member=self.member, place=self.place).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_user_can_unsave_place(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")
        Favorite.objects.create(member=self.member, place=self.place)

        response = self.client.delete(favorite_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Favorite.objects.filter(member=self.member, place=self.place).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_my_favorite_list_shows_saved_places(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")
        other_place = Place.objects.create(name="남산타워", address="서울시 용산구")
        Favorite.objects.create(member=self.member, place=self.place)
        Favorite.objects.create(member=self.member, place=other_place)

        response = self.client.get(MY_FAVORITES_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["favorites"]), 2)
        place_names = {f["place"]["name"] for f in response.data["favorites"]}
        self.assertEqual(place_names, {"경복궁", "남산타워"})

    @patch("accounts.authentication.verify_id_token")
    def test_saving_same_place_twice_does_not_duplicate_in_db(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")

        first = self.client.post(favorite_url(self.place.id), **self.auth_header)
        second = self.client.post(favorite_url(self.place.id), **self.auth_header)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        # DB에 실제로 1건만 있는지 직접 확인 (compound-log 2026-08-19 교훈: 응답만 보고 통과시키지 않는다)
        self.assertEqual(Favorite.objects.filter(member=self.member, place=self.place).count(), 1)

    @patch("accounts.authentication.verify_id_token")
    def test_unsaving_place_never_saved_is_not_an_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")

        response = self.client.delete(favorite_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_anonymous_user_cannot_save_place(self):
        response = self.client.post(favorite_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    def test_anonymous_user_cannot_unsave_place(self):
        response = self.client.delete(favorite_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    def test_anonymous_user_cannot_see_my_favorite_list(self):
        response = self.client.get(MY_FAVORITES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_cannot_save_place(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.post(favorite_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "다시 로그인하세요")

    @patch("accounts.authentication.verify_id_token")
    def test_saving_nonexistent_place_returns_404(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")

        response = self.client.post(favorite_url(999999), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_place_detail_is_favorited_false_when_anonymous(self):
        response = self.client.get(place_detail_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_favorited"])

    @patch("accounts.authentication.verify_id_token")
    def test_place_detail_is_favorited_false_when_not_saved(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")

        response = self.client.get(place_detail_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_favorited"])

    @patch("accounts.authentication.verify_id_token")
    def test_place_detail_is_favorited_true_when_saved(self, mock_verify):
        mock_verify.return_value = make_decoded_token("fav-uid-1")
        Favorite.objects.create(member=self.member, place=self.place)

        response = self.client.get(place_detail_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_favorited"])

    @patch("accounts.authentication.verify_id_token")
    def test_place_detail_is_favorited_only_reflects_requesting_member(self, mock_verify):
        # 다른 회원이 저장한 건 내 즐겨찾기에 영향을 주면 안 된다.
        other_member = create_member("fav-uid-other")
        Favorite.objects.create(member=other_member, place=self.place)
        mock_verify.return_value = make_decoded_token("fav-uid-1")

        response = self.client.get(place_detail_url(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["is_favorited"])
