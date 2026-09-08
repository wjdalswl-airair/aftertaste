"""AI 코스 추천(DETAIL_SPEC 6-1 #31) 테스트.

Claude 호출과 카카오 주변 상권 조회는 전부 목킹한다 — 실제 외부 API를 부르지 않는다.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from courses.ai_recommendation import role_of
from courses.models import Course
from places.models import Place

from courses.tests import create_member, make_decoded_token

AI_URL = "/api/places/{place_id}/courses/ai-recommend/"


def nearby_candidates():
    """식당·카페·그 외가 하나씩 든 정상 후보 목록 (카카오 응답 모양)."""
    return [
        {
            "id": "r1",
            "place_name": "한옥집",
            "address_name": "서울시 종로구 1",
            "road_address_name": "서울시 종로구 1로",
            "latitude": 37.580,
            "longitude": 126.970,
            "category_name": "음식점 > 한식",
        },
        {
            "id": "c1",
            "place_name": "정독카페",
            "address_name": "서울시 종로구 2",
            "road_address_name": "서울시 종로구 2로",
            "latitude": 37.581,
            "longitude": 126.971,
            "category_name": "카페 > 커피전문점",
        },
        {
            "id": "o1",
            "place_name": "국립현대미술관 서울",
            "address_name": "서울시 종로구 3",
            "road_address_name": "서울시 종로구 3로",
            "latitude": 37.579,
            "longitude": 126.980,
            "category_name": "문화,예술 > 미술관",
        },
    ]


def fake_tool_response(**tool_input):
    """Claude가 submit_course 도구로 답한 응답을 흉내 낸다."""
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="text", text="코스를 만들었어요"),
            SimpleNamespace(type="tool_use", name="submit_course", input=tool_input),
        ]
    )


VALID_TOOL_INPUT = {
    "title": "한옥 나들이",
    "description": "고즈넉한 오후 산책",
    "restaurant_ref": 0,
    "cafe_ref": 1,
    "other_ref": 2,
    "visit_order": ["OTHER", "RESTAURANT", "CAFE"],
}


@override_settings(ANTHROPIC_API_KEY="test-key")
class AiRecommendTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = create_member("ai-course-uid")
        self.place = Place.objects.create(
            name="경복궁", address="서울시 종로구", latitude=37.5796, longitude=126.977
        )

    def url(self):
        return AI_URL.format(place_id=self.place.id)

    @patch("courses.ai_recommendation.anthropic.Anthropic")
    @patch("courses.views._fetch_nearby_places")
    @patch("accounts.authentication.verify_id_token")
    def test_creates_course_from_ai_picks(self, mock_verify, mock_nearby, mock_anthropic):
        mock_verify.return_value = make_decoded_token("ai-course-uid")
        mock_nearby.return_value = nearby_candidates()
        mock_anthropic.return_value.messages.create.return_value = fake_tool_response(**VALID_TOOL_INPUT)

        response = self.client.post(self.url(), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course = Course.objects.get(pk=response.data["id"])
        self.assertEqual(course.creator_id, self.member.id)
        self.assertEqual(course.place_id, self.place.id)
        self.assertEqual(course.title, "한옥 나들이")

        places = list(course.course_places.order_by("order"))
        self.assertEqual([p.role for p in places], ["OTHER", "RESTAURANT", "CAFE"])
        self.assertEqual(places[0].name, "국립현대미술관 서울")
        self.assertEqual(places[1].name, "한옥집")
        self.assertEqual(places[2].kakao_place_id, "c1")

    @patch("courses.ai_recommendation.anthropic.Anthropic")
    @patch("courses.views._fetch_nearby_places")
    def test_requires_login(self, mock_nearby, mock_anthropic):
        mock_nearby.return_value = nearby_candidates()

        response = self.client.post(self.url())

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertFalse(mock_anthropic.called)
        self.assertEqual(Course.objects.count(), 0)

    @patch("accounts.authentication.verify_id_token")
    def test_place_not_found_returns_404(self, mock_verify):
        mock_verify.return_value = make_decoded_token("ai-course-uid")

        response = self.client.post(AI_URL.format(place_id=999999), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("courses.ai_recommendation.anthropic.Anthropic")
    @patch("courses.views._fetch_nearby_places")
    @patch("accounts.authentication.verify_id_token")
    def test_place_with_existing_course_returns_400(self, mock_verify, mock_nearby, mock_anthropic):
        mock_verify.return_value = make_decoded_token("ai-course-uid")
        Course.objects.create(place=self.place, creator=self.member, title="이미 있는 코스")

        response = self.client.post(self.url(), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(mock_anthropic.called)
        self.assertFalse(mock_nearby.called)
        self.assertEqual(Course.objects.count(), 1)

    @patch("courses.ai_recommendation.anthropic.Anthropic")
    @patch("courses.views._fetch_nearby_places")
    @patch("accounts.authentication.verify_id_token")
    def test_insufficient_candidates_returns_422(self, mock_verify, mock_nearby, mock_anthropic):
        mock_verify.return_value = make_decoded_token("ai-course-uid")
        # 카페 후보가 없다 (식당 + 그 외만)
        mock_nearby.return_value = [nearby_candidates()[0], nearby_candidates()[2]]

        response = self.client.post(self.url(), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(mock_anthropic.called)
        self.assertEqual(Course.objects.count(), 0)

    @patch("courses.ai_recommendation.anthropic.Anthropic")
    @patch("courses.views._fetch_nearby_places")
    @patch("accounts.authentication.verify_id_token")
    def test_claude_failure_returns_503(self, mock_verify, mock_nearby, mock_anthropic):
        import anthropic

        mock_verify.return_value = make_decoded_token("ai-course-uid")
        mock_nearby.return_value = nearby_candidates()
        mock_anthropic.return_value.messages.create.side_effect = anthropic.AnthropicError("boom")

        response = self.client.post(self.url(), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(Course.objects.count(), 0)

    @override_settings(ANTHROPIC_API_KEY="")
    @patch("courses.views._fetch_nearby_places")
    @patch("accounts.authentication.verify_id_token")
    def test_missing_api_key_returns_503(self, mock_verify, mock_nearby):
        mock_verify.return_value = make_decoded_token("ai-course-uid")
        mock_nearby.return_value = nearby_candidates()

        response = self.client.post(self.url(), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(Course.objects.count(), 0)

    @patch("courses.ai_recommendation.anthropic.Anthropic")
    @patch("courses.views._fetch_nearby_places")
    @patch("accounts.authentication.verify_id_token")
    def test_model_picks_unknown_ref_falls_back(self, mock_verify, mock_nearby, mock_anthropic):
        mock_verify.return_value = make_decoded_token("ai-course-uid")
        mock_nearby.return_value = nearby_candidates()
        bad_input = {**VALID_TOOL_INPUT, "restaurant_ref": 99, "visit_order": ["bad"]}
        mock_anthropic.return_value.messages.create.return_value = fake_tool_response(**bad_input)

        response = self.client.post(self.url(), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course = Course.objects.get(pk=response.data["id"])
        # 잘못된 ref는 그 role의 첫 후보(한옥집)로 대체되고, 이상한 순서는 기본 순서로 돌아간다.
        places = list(course.course_places.order_by("order"))
        self.assertEqual([p.role for p in places], ["RESTAURANT", "CAFE", "OTHER"])
        self.assertEqual(places[0].name, "한옥집")


class RoleOfTests(TestCase):
    def test_maps_category_string_to_course_role(self):
        self.assertEqual(role_of("음식점 > 한식 > 국밥"), "RESTAURANT")
        self.assertEqual(role_of("카페 > 커피전문점"), "CAFE")
        self.assertEqual(role_of("문화,예술 > 미술관"), "OTHER")
        self.assertEqual(role_of(None), "OTHER")
        self.assertEqual(role_of(""), "OTHER")
