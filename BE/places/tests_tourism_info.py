"""주변 관광정보 API(GET /api/places/<id>/tourism-info/, 이슈 #76) 테스트.

한국관광공사 TourAPI는 mock으로 처리해 실제 네트워크 호출을 하지 않는다.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase

from places.models import Place
from places.sources import tour_api

URL_TEMPLATE = "/api/places/{}/tourism-info/"


def _item(category, name, distance=100):
    return {
        "category": category,
        "name": name,
        "address": "서울 종로구 1",
        "image_url": "",
        "latitude": 37.58,
        "longitude": 126.98,
        "distance": distance,
        "tel": "",
    }


class PlaceTourismInfoViewTest(TestCase):
    def setUp(self):
        # 서버 메모리 캐시가 테스트끼리 섞이지 않게 비운다.
        cache.clear()
        self.place = Place.objects.create(name="경복궁", latitude=Decimal("37.5796"), longitude=Decimal("126.9769"))

    @patch("places.views.tour_api.search_nearby")
    def test_default_returns_all_six_categories_in_order(self, mock_search):
        mock_search.side_effect = lambda lat, lng, radius, category, n: [_item(category, category + "1")]

        response = self.client.get(URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, 200)
        categories = [item["category"] for item in response.data["results"]]
        self.assertEqual(categories, ["food", "lodging", "experience", "history", "nature", "culture"])
        self.assertEqual(set(response.data["results"][0]), {
            "category", "name", "address", "image_url", "latitude", "longitude", "distance", "tel",
        })

    @patch("places.views.tour_api.search_nearby")
    def test_category_filter_calls_only_requested_categories(self, mock_search):
        mock_search.side_effect = lambda lat, lng, radius, category, n: [_item(category, category + "1")]

        response = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food, history,food"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([i["category"] for i in response.data["results"]], ["food", "history"])
        self.assertEqual(mock_search.call_count, 2)

    @patch("places.views.tour_api.search_nearby")
    def test_passes_place_coordinates_and_radius(self, mock_search):
        mock_search.return_value = []

        self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food", "radius": "500"})

        lat, lng, radius, category, _limit = mock_search.call_args.args
        self.assertEqual((lat, lng, radius, category), (37.5796, 126.9769, 500, "food"))

    @patch("places.views.tour_api.search_nearby")
    def test_default_radius_is_1000(self, mock_search):
        mock_search.return_value = []

        self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food"})

        self.assertEqual(mock_search.call_args.args[2], 1000)

    @patch("places.views.tour_api.search_nearby")
    def test_invalid_category_is_400(self, mock_search):
        response = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food,pizza"})

        self.assertEqual(response.status_code, 400)
        mock_search.assert_not_called()

    @patch("places.views.tour_api.search_nearby")
    def test_invalid_radius_is_400(self, mock_search):
        for bad in ("abc", "0", "-5", "20001"):
            response = self.client.get(URL_TEMPLATE.format(self.place.id), {"radius": bad})
            self.assertEqual(response.status_code, 400, bad)
        mock_search.assert_not_called()

    @patch("places.views.tour_api.search_nearby")
    def test_unknown_place_is_404(self, mock_search):
        response = self.client.get(URL_TEMPLATE.format(999999))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "존재하지 않습니다")
        mock_search.assert_not_called()

    @patch("places.views.tour_api.search_nearby")
    def test_place_without_coordinates_returns_empty_list(self, mock_search):
        place = Place.objects.create(name="좌표 없음")

        response = self.client.get(URL_TEMPLATE.format(place.id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"results": []})
        mock_search.assert_not_called()

    @patch("places.views.tour_api.search_nearby")
    def test_partial_failure_returns_successful_categories(self, mock_search):
        def fake(lat, lng, radius, category, n):
            if category == "lodging":
                raise RuntimeError("TourAPI 오류")
            return [_item(category, category + "1")]

        mock_search.side_effect = fake

        response = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food,lodging,history"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([i["category"] for i in response.data["results"]], ["food", "history"])

    @patch("places.views.tour_api.search_nearby")
    def test_all_categories_failing_is_503(self, mock_search):
        mock_search.side_effect = tour_api.TourApiDailyLimitError("일일 한도 초과")

        response = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food,history"})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["detail"], "관광정보를 잠시 불러올 수 없습니다.")

    @patch("places.views.tour_api.search_nearby")
    def test_empty_result_is_ok_not_error(self, mock_search):
        mock_search.return_value = []

        response = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "nature"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"results": []})

    @patch("places.views.tour_api.search_nearby")
    def test_same_request_is_served_from_memory_cache(self, mock_search):
        mock_search.return_value = [_item("food", "식당")]

        first = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food"})
        second = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food"})

        self.assertEqual(first.data, second.data)
        self.assertEqual(mock_search.call_count, 1)

    @patch("places.views.tour_api.search_nearby")
    def test_empty_result_is_cached_too(self, mock_search):
        mock_search.return_value = []

        self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "nature"})
        self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "nature"})

        self.assertEqual(mock_search.call_count, 1)

    @patch("places.views.tour_api.search_nearby")
    def test_failure_is_not_cached(self, mock_search):
        mock_search.side_effect = [RuntimeError("일시 오류"), [_item("food", "식당")]]

        first = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food"})
        second = self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food"})

        self.assertEqual(first.status_code, 503)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(second.data["results"]), 1)

    @patch("places.views.tour_api.search_nearby")
    def test_different_radius_is_cached_separately(self, mock_search):
        mock_search.return_value = []

        self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food", "radius": "500"})
        self.client.get(URL_TEMPLATE.format(self.place.id), {"category": "food", "radius": "800"})

        self.assertEqual(mock_search.call_count, 2)

    @patch("places.views.tour_api.search_nearby")
    def test_invalid_token_does_not_block_anonymous_read(self, mock_search):
        mock_search.return_value = []

        response = self.client.get(
            URL_TEMPLATE.format(self.place.id), {"category": "food"}, HTTP_AUTHORIZATION="Bearer invalid"
        )

        self.assertEqual(response.status_code, 200)


class TourApiSearchNearbyTest(TestCase):
    """tour_api.search_nearby가 TourAPI 응답을 우리 응답 모양으로 바꾸는지. requests.get을 mock한다."""

    def _response(self, payload):
        class FakeResponse:
            status_code = 200
            text = ""

            def raise_for_status(self):
                pass

            def json(self):
                return payload

        return FakeResponse()

    def _payload(self, items):
        return {"response": {"header": {"resultCode": "0000"}, "body": {"items": items, "totalCount": 1}}}

    @patch("places.sources.tour_api._get_service_key", return_value="test-key")
    @patch("places.sources.tour_api.requests.get")
    def test_normalizes_item_and_sends_expected_params(self, mock_get, _key):
        row = {
            "title": "국립현대미술관 서울",
            "addr1": "서울특별시 종로구 삼청로 30",
            "addr2": "(소격동)",
            "firstimage": "http://img/1.jpg",
            "firstimage2": "http://img/1s.jpg",
            "mapx": "126.9800038741",
            "mapy": "37.5786500878",
            "dist": "295.3937109061377",
            "tel": "02-000-0000",
        }
        mock_get.return_value = self._response(self._payload({"item": [row]}))

        result = tour_api.search_nearby(37.5796, 126.9769, 1000, "culture", 10)

        self.assertEqual(result, [{
            "category": "culture",
            "name": "국립현대미술관 서울",
            "address": "서울특별시 종로구 삼청로 30 (소격동)",
            "image_url": "http://img/1.jpg",
            "latitude": 37.5786500878,
            "longitude": 126.9800038741,
            "distance": 295,
            "tel": "02-000-0000",
        }])
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["lclsSystm1"], "VE")
        self.assertEqual(params["mapX"], 126.9769)
        self.assertEqual(params["mapY"], 37.5796)
        self.assertEqual(params["radius"], 1000)
        self.assertEqual(params["arrange"], "E")
        self.assertEqual(params["numOfRows"], 10)
        # 화면 요청 중 호출이라 배치용(30초)보다 짧은 타임아웃을 쓴다.
        self.assertLess(mock_get.call_args.kwargs["timeout"], 30)

    @patch("places.sources.tour_api._get_service_key", return_value="test-key")
    @patch("places.sources.tour_api.requests.get")
    def test_single_result_dict_and_missing_fields(self, mock_get, _key):
        # 결과가 1건이면 item이 리스트가 아니라 dict로 오고, 이미지·전화가 없으면 빈 문자열이 된다.
        row = {"title": "작은 가게", "addr1": "서울 어딘가", "mapx": "127.0", "mapy": "37.5", "dist": "0"}
        mock_get.return_value = self._response(self._payload({"item": row}))

        result = tour_api.search_nearby(37.5, 127.0, 500, "food", 10)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["image_url"], "")
        self.assertEqual(result[0]["tel"], "")
        self.assertEqual(result[0]["distance"], 0)

    @patch("places.sources.tour_api._get_service_key", return_value="test-key")
    @patch("places.sources.tour_api.requests.get")
    def test_no_results_returns_empty_list(self, mock_get, _key):
        # 결과가 없으면 items가 빈 문자열("")로 온다.
        mock_get.return_value = self._response(self._payload(""))

        self.assertEqual(tour_api.search_nearby(37.5, 127.0, 500, "nature", 10), [])
