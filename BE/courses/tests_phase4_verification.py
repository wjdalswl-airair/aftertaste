"""Phase4 코스(F-08) 테스트 에이전트가 기존 courses/tests.py에서 빠진 항목을 보강하기 위해
추가한 검증용 테스트. (테스트 전담 에이전트 작성 - 구현 코드는 건드리지 않는다)

빠진 항목:
- role이 3개보다 많을 때(예: 4개, RESTAURANT 중복) 400
- 무효 토큰으로 명소 기준 코스 "목록"(PlaceCourseListCreateView GET)을 조회해도 막히지 않는다
  (CourseDetailView는 courses/tests.py에 있었지만 목록 쪽은 빠져 있었다)
- 서로 다른 명소(anchor)를 기준으로 하는 코스가 섞이지 않는다
- Favorite의 CheckConstraint(정확히 하나만 채워짐)가 DB 레벨에서 실제로 막는다
  (place/course 둘 다 채움, 둘 다 비움 각각)
"""

from unittest.mock import patch

from django.db import IntegrityError, transaction
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
    return [
        {
            "role": "RESTAURANT", "name": "맛집", "address": "서울시 종로구 1길",
            "road_address_name": "서울시 종로구 1로", "latitude": 37.5, "longitude": 126.9,
            "category_name": "음식점 > 한식", "kakao_place_id": "111",
        },
        {
            "role": "CAFE", "name": "카페", "address": "서울시 종로구 2길",
            "road_address_name": "서울시 종로구 2로", "latitude": 37.51, "longitude": 126.91,
            "category_name": "카페", "kakao_place_id": "222",
        },
        {
            "role": "OTHER", "name": "소품샵", "address": "서울시 종로구 3길",
            "road_address_name": "서울시 종로구 3로", "latitude": 37.52, "longitude": 126.92,
            "category_name": "가정,생활 > 소품샵", "kakao_place_id": "333",
        },
    ]


class TooManyRolesTests(TestCase):
    """role이 3개보다 많으면(4개) 400이어야 한다."""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = create_member("too-many-roles-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")

    @patch("accounts.authentication.verify_id_token")
    def test_four_places_returns_400(self, mock_verify):
        mock_verify.return_value = make_decoded_token("too-many-roles-uid")
        places = valid_course_places() + [
            {
                "role": "RESTAURANT", "name": "맛집2", "address": "서울시 종로구 4길",
                "road_address_name": "서울시 종로구 4로", "latitude": 37.53, "longitude": 126.93,
                "category_name": "음식점 > 중식", "kakao_place_id": "444",
            }
        ]

        response = self.client.post(
            place_courses_url(self.place.id),
            {"title": "궁궐 나들이", "course_places": places},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)


class PlaceCourseListInvalidTokenTests(TestCase):
    """PlaceCourseListCreateView의 GET(목록)도 CourseDetailView와 마찬가지로
    무효/만료 토큰이 조회를 막으면 안 된다. courses/tests.py는 상세(CourseDetailView)만
    검증했고 목록 쪽은 검증하지 않아 이 항목을 추가한다."""

    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.course = Course.objects.create(place=self.place, title="궁궐 나들이")
        for order, item in enumerate(valid_course_places()):
            CoursePlace.objects.create(course=self.course, order=order, **item)

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_can_still_list_courses(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(
            place_courses_url(self.place.id), HTTP_AUTHORIZATION="Bearer fake-token"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["courses"]), 1)


class DifferentAnchorPlaceIsolationTests(TestCase):
    """서로 다른 명소를 anchor로 하는 코스가 섞이지 않는다."""

    def setUp(self):
        self.client = APIClient()
        self.place_a = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.place_b = Place.objects.create(name="남산타워", address="서울시 용산구")
        self.course_a = Course.objects.create(place=self.place_a, title="A 코스")
        self.course_b = Course.objects.create(place=self.place_b, title="B 코스")
        # 카카오 식별자가 서로 겹치지 않게 각각 다른 kakao_place_id를 쓴다.
        for order, item in enumerate(valid_course_places()):
            CoursePlace.objects.create(course=self.course_a, order=order, **item)
        b_places = valid_course_places()
        for item in b_places:
            item["kakao_place_id"] = "b-" + item["kakao_place_id"]
        for order, item in enumerate(b_places):
            CoursePlace.objects.create(course=self.course_b, order=order, **item)

    def test_place_a_list_does_not_include_place_b_course(self):
        response = self.client.get(place_courses_url(self.place_a.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [c["title"] for c in response.data["courses"]]
        self.assertEqual(titles, ["A 코스"])

    def test_place_b_list_does_not_include_place_a_course(self):
        response = self.client.get(place_courses_url(self.place_b.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [c["title"] for c in response.data["courses"]]
        self.assertEqual(titles, ["B 코스"])


class FavoriteCheckConstraintTests(TestCase):
    """Favorite에 place/course가 둘 다 채워지거나 둘 다 비어있으면 DB CheckConstraint가 막는다."""

    def setUp(self):
        self.member = create_member("constraint-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.course = Course.objects.create(place=self.place, title="궁궐 나들이")

    def test_both_place_and_course_filled_is_rejected_by_db(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(member=self.member, place=self.place, course=self.course)

    def test_neither_place_nor_course_filled_is_rejected_by_db(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Favorite.objects.create(member=self.member)
