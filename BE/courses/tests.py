"""Phase 4 코스(F-08) 체크리스트를 검증하는 테스트.

DETAIL_SPEC.md 6-1 #17 / PHASES/PHASE4.md 4-1(코스 추천) 완료 기준 체크리스트를 근거로 만들었다.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.firebase import InvalidFirebaseToken
from accounts.models import Member
from courses.models import Course, CoursePlace
from favorites.models import Favorite
from places.models import Place


def place_courses_url(place_id):
    return f"/api/places/{place_id}/courses/"


def course_detail_url(course_id):
    return f"/api/courses/{course_id}/"


def course_favorite_url(course_id):
    return f"/api/courses/{course_id}/favorite/"


MY_COURSES_URL = "/api/account/courses/"
MY_FAVORITES_URL = "/api/account/favorites/"


def make_decoded_token(uid):
    return {
        "uid": uid,
        "email": f"{uid}@example.com",
        "name": "테스터",
        "picture": "http://example.com/pic.jpg",
        "firebase": {"sign_in_provider": "google.com"},
    }


def create_member(uid, nickname="회원"):
    return Member.objects.create(
        firebase_uid=uid,
        provider=Member.Provider.GOOGLE,
        nickname=nickname,
        agreed_terms_at="2026-01-01T00:00:00Z",
    )


def valid_course_places():
    """식당 1 + 카페 1 + 그 외 1로 구성된 정상적인 course_places 입력."""
    return [
        {
            "role": "RESTAURANT",
            "name": "맛집",
            "address": "서울시 종로구 1길",
            "road_address_name": "서울시 종로구 1로",
            "latitude": 37.5,
            "longitude": 126.9,
            "category_name": "음식점 > 한식",
            "kakao_place_id": "111",
        },
        {
            "role": "CAFE",
            "name": "카페",
            "address": "서울시 종로구 2길",
            "road_address_name": "서울시 종로구 2로",
            "latitude": 37.51,
            "longitude": 126.91,
            "category_name": "카페",
            "kakao_place_id": "222",
        },
        {
            "role": "OTHER",
            "name": "소품샵",
            "address": "서울시 종로구 3길",
            "road_address_name": "서울시 종로구 3로",
            "latitude": 37.52,
            "longitude": 126.92,
            "category_name": "가정,생활 > 소품샵",
            "kakao_place_id": "333",
        },
    ]


class CourseCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = create_member("course-creator-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")

    @patch("accounts.authentication.verify_id_token")
    def test_course_with_restaurant_cafe_other_is_created(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-creator-uid")

        response = self.client.post(
            place_courses_url(self.place.id),
            {"title": "궁궐 나들이", "description": "설명", "course_places": valid_course_places()},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course = Course.objects.get(pk=response.data["id"])
        self.assertEqual(course.creator_id, self.member.id)
        self.assertEqual(course.place_id, self.place.id)
        roles = set(course.course_places.values_list("role", flat=True))
        self.assertEqual(roles, {"RESTAURANT", "CAFE", "OTHER"})
        self.assertEqual(course.course_places.count(), 3)

    @patch("accounts.authentication.verify_id_token")
    def test_missing_a_role_returns_400(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-creator-uid")
        places = valid_course_places()[:2]  # 식당 + 카페만, 그 외가 빠짐

        response = self.client.post(
            place_courses_url(self.place.id),
            {"title": "궁궐 나들이", "course_places": places},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)

    @patch("accounts.authentication.verify_id_token")
    def test_duplicate_role_returns_400(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-creator-uid")
        places = valid_course_places()
        places[2]["role"] = "CAFE"  # 그 외 자리에 카페를 중복으로 넣음 (RESTAURANT 없음)

        response = self.client.post(
            place_courses_url(self.place.id),
            {"title": "궁궐 나들이", "course_places": places},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)

    def test_anonymous_cannot_create_course(self):
        response = self.client.post(
            place_courses_url(self.place.id),
            {"title": "궁궐 나들이", "course_places": valid_course_places()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    @patch("accounts.authentication.verify_id_token")
    def test_creating_course_for_nonexistent_place_returns_404(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-creator-uid")

        response = self.client.post(
            place_courses_url(999999),
            {"title": "궁궐 나들이", "course_places": valid_course_places()},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CourseReadTests(TestCase):
    """명소 상세에서 코스로 들어가는 진입점(목록) + 상세는 로그인 없이 볼 수 있어야 한다."""

    def setUp(self):
        self.client = APIClient()
        self.member = create_member("course-owner-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.course = Course.objects.create(place=self.place, creator=self.member, title="궁궐 나들이")
        for order, item in enumerate(valid_course_places()):
            CoursePlace.objects.create(course=self.course, order=order, **item)

    def test_anonymous_can_list_courses_of_a_place(self):
        response = self.client.get(place_courses_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["courses"]), 1)
        self.assertEqual(len(response.data["courses"][0]["course_places"]), 3)

    def test_anonymous_can_view_course_detail(self):
        response = self.client.get(course_detail_url(self.course.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "궁궐 나들이")
        self.assertEqual(response.data["place_id"], self.place.id)

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_can_still_view_course_detail(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(course_detail_url(self.course.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_viewing_nonexistent_course_returns_404(self):
        response = self.client.get(course_detail_url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CourseEditDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = create_member("course-owner-uid", nickname="주인")
        self.other = create_member("course-other-uid", nickname="남")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.course = Course.objects.create(place=self.place, creator=self.owner, title="원래 제목")
        for order, item in enumerate(valid_course_places()):
            CoursePlace.objects.create(course=self.course, order=order, **item)

    @patch("accounts.authentication.verify_id_token")
    def test_owner_can_update_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-owner-uid")

        response = self.client.patch(
            course_detail_url(self.course.id),
            {"title": "새 제목"},
            format="json",
            HTTP_AUTHORIZATION="Bearer fake-token",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "새 제목")

    @patch("accounts.authentication.verify_id_token")
    def test_non_owner_cannot_update_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-other-uid")

        response = self.client.patch(
            course_detail_url(self.course.id),
            {"title": "새 제목"},
            format="json",
            HTTP_AUTHORIZATION="Bearer fake-token",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, "원래 제목")

    @patch("accounts.authentication.verify_id_token")
    def test_owner_can_delete_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-owner-uid")

        response = self.client.delete(course_detail_url(self.course.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=self.course.id).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_non_owner_cannot_delete_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-other-uid")

        response = self.client.delete(course_detail_url(self.course.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Course.objects.filter(pk=self.course.id).exists())

    def test_anonymous_cannot_update_course(self):
        response = self.client.patch(course_detail_url(self.course.id), {"title": "새 제목"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_cannot_delete_course(self):
        response = self.client.delete(course_detail_url(self.course.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MyCourseListTests(TestCase):
    """저장한(만든) 코스가 마이페이지에 나온다."""

    def setUp(self):
        self.client = APIClient()
        self.member = create_member("course-owner-uid")
        self.other = create_member("course-other-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")

    @patch("accounts.authentication.verify_id_token")
    def test_my_course_list_shows_only_my_courses(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-owner-uid")
        Course.objects.create(place=self.place, creator=self.member, title="내 코스")
        Course.objects.create(place=self.place, creator=self.other, title="남의 코스")

        response = self.client.get(MY_COURSES_URL, HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [c["title"] for c in response.data["courses"]]
        self.assertEqual(titles, ["내 코스"])

    def test_anonymous_cannot_see_my_course_list(self):
        response = self.client.get(MY_COURSES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CourseFavoriteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = create_member("course-fan-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.course = Course.objects.create(place=self.place, title="궁궐 나들이")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_user_can_favorite_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-fan-uid")

        response = self.client.post(course_favorite_url(self.course.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Favorite.objects.filter(member=self.member, course=self.course).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_favoriting_same_course_twice_does_not_duplicate_or_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-fan-uid")

        first = self.client.post(course_favorite_url(self.course.id), **self.auth_header)
        second = self.client.post(course_favorite_url(self.course.id), **self.auth_header)

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Favorite.objects.filter(member=self.member, course=self.course).count(), 1)

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_user_can_unfavorite_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-fan-uid")
        Favorite.objects.create(member=self.member, course=self.course)

        response = self.client.delete(course_favorite_url(self.course.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Favorite.objects.filter(member=self.member, course=self.course).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_unfavoriting_course_never_favorited_is_not_an_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-fan-uid")

        response = self.client.delete(course_favorite_url(self.course.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_anonymous_cannot_favorite_course(self):
        response = self.client.post(course_favorite_url(self.course.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_favorited_course_appears_in_my_favorite_list_with_type_course(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-fan-uid")
        Favorite.objects.create(member=self.member, course=self.course)

        response = self.client.get(MY_FAVORITES_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["favorites"]), 1)
        favorite = response.data["favorites"][0]
        self.assertEqual(favorite["type"], "COURSE")
        self.assertIsNone(favorite["place"])
        self.assertEqual(favorite["course"]["id"], self.course.id)

    @patch("accounts.authentication.verify_id_token")
    def test_place_and_course_favorites_both_appear_in_my_favorite_list(self, mock_verify):
        mock_verify.return_value = make_decoded_token("course-fan-uid")
        Favorite.objects.create(member=self.member, place=self.place)
        Favorite.objects.create(member=self.member, course=self.course)

        response = self.client.get(MY_FAVORITES_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        types = {f["type"] for f in response.data["favorites"]}
        self.assertEqual(types, {"PLACE", "COURSE"})
