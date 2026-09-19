"""GET /api/courses/ (코스 탭 전체 코스 목록, issue #74) 테스트."""

from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Member
from courses.models import Course
from favorites.models import Favorite
from places.models import Place

COURSE_LIST_URL = "/api/courses/"


def create_member(uid):
    return Member.objects.create(
        firebase_uid=uid,
        provider=Member.Provider.GOOGLE,
        nickname=uid,
        agreed_terms_at="2026-01-01T00:00:00Z",
    )


class CourseListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(
            name="경복궁",
            address="서울시 종로구",
            latitude=Decimal("37.579771"),
            longitude=Decimal("126.977041"),
        )

    def test_anonymous_can_list_courses_with_anchor_place_info(self):
        course = Course.objects.create(place=self.place, title="궁궐 나들이")

        response = self.client.get(COURSE_LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["courses"][0],
            {
                "id": course.id,
                "title": "궁궐 나들이",
                "place_id": self.place.id,
                "place_name": "경복궁",
                "latitude": 37.579771,
                "longitude": 126.977041,
                "favorite_count": 0,
            },
        )

    def test_invalid_token_does_not_block_listing(self):
        Course.objects.create(place=self.place, title="코스")

        response = self.client.get(COURSE_LIST_URL, HTTP_AUTHORIZATION="Bearer broken")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_favorite_count_counts_only_that_course(self):
        popular = Course.objects.create(place=self.place, title="인기 코스")
        Course.objects.create(place=self.place, title="조용한 코스")
        for uid in ("fan-1", "fan-2"):
            Favorite.objects.create(member=create_member(uid), course=popular)
        # 명소 즐겨찾기는 코스의 favorite_count에 섞이면 안 된다.
        Favorite.objects.create(member=create_member("place-fan"), place=self.place)

        response = self.client.get(COURSE_LIST_URL)

        counts = {c["title"]: c["favorite_count"] for c in response.data["courses"]}
        self.assertEqual(counts, {"인기 코스": 2, "조용한 코스": 0})

    def test_courses_are_newest_first(self):
        first = Course.objects.create(place=self.place, title="먼저")
        second = Course.objects.create(place=self.place, title="나중")

        response = self.client.get(COURSE_LIST_URL)

        self.assertEqual([c["id"] for c in response.data["courses"]], [second.id, first.id])

    def test_place_without_coordinates_gives_null(self):
        bare_place = Place.objects.create(name="좌표 없는 곳", address="어딘가")
        Course.objects.create(place=bare_place, title="좌표 없는 코스")

        response = self.client.get(COURSE_LIST_URL)

        course = response.data["courses"][0]
        self.assertIsNone(course["latitude"])
        self.assertIsNone(course["longitude"])

    def test_pagination_splits_pages(self):
        for i in range(3):
            Course.objects.create(place=self.place, title=f"코스{i}")

        page1 = self.client.get(COURSE_LIST_URL, {"page_size": 2})
        page2 = self.client.get(COURSE_LIST_URL, {"page_size": 2, "page": 2})

        self.assertEqual(page1.data["count"], 3)
        self.assertEqual(len(page1.data["courses"]), 2)
        self.assertIsNotNone(page1.data["next"])
        self.assertEqual(len(page2.data["courses"]), 1)
        self.assertIsNone(page2.data["next"])

    def test_list_query_count_does_not_grow_with_courses(self):
        for i in range(5):
            Course.objects.create(place=self.place, title=f"코스{i}")

        # 개수 조회 1 + 목록 조회 1 (place는 join, favorite_count는 annotate).
        with self.assertNumQueries(2):
            self.client.get(COURSE_LIST_URL)
