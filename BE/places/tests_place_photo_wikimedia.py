"""feature/be/place-photo: 한국어 위키백과로 명소(Place) 대표 사진(photo_url) 보강.

TourAPI 보강(tests_place_photo_enrichment.py)과 규칙은 같고 소스만 다르다. 여기서는
위키백과 쪽에만 있는 것을 확인한다.
- 위키백과 API 응답을 tour_api와 같은 dict 모양으로 정규화하는지 (wikimedia._normalize_page)
- WIKIMEDIA PlaceSource에 pageid를 남기고, 재실행 때 재검색 대신 그 id로 조회하는지
- 기본 실행이 TourAPI로 이미 채운 명소는 건드리지 않고, 못 채운 명소만 이어서 시도하는지
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from places.models import Place, PlaceSource
from places.place_photo_enrichment import (
    TOUR_API_SOURCE,
    WIKIMEDIA_SOURCE,
    enrich_place_photo_from_wikimedia,
)
from places.sources import wikimedia


_COMMONS = "https://upload.wikimedia.org/wikipedia/commons/a/a1"


def _candidate(title, *, image=f"{_COMMONS}/a.jpg", lat=37.5665, lng=126.9780, content_id="1"):
    return {
        "content_id": content_id,
        "content_type_id": None,
        "title": title,
        "address": "",
        "latitude": lat,
        "longitude": lng,
        "first_image": image,
    }


class NormalizePageTest(TestCase):
    def test_maps_wikipedia_fields_to_common_shape_and_strips_tracking_query(self):
        page = {
            "pageid": 12345,
            "title": "경복궁",
            # API는 대표 이미지 URL에 추적용 쿼리스트링(?utm_source=...)을 붙여서 준다.
            "original": {
                "source": f"{_COMMONS}/gbg.jpg?utm_source=ko.wikipedia.org&utm_campaign=api"
            },
            "coordinates": [{"lat": 37.5796, "lon": 126.9770, "primary": True}],
        }
        self.assertEqual(
            wikimedia._normalize_page(page),
            {
                "content_id": "12345",
                "content_type_id": None,
                "title": "경복궁",
                "address": "",
                "latitude": 37.5796,
                "longitude": 126.9770,
                "first_image": f"{_COMMONS}/gbg.jpg",
            },
        )

    def test_page_without_image_or_coords(self):
        page = {"pageid": 7, "title": "어떤 카페"}
        result = wikimedia._normalize_page(page)
        self.assertEqual(result["first_image"], "")
        self.assertIsNone(result["latitude"])
        self.assertIsNone(result["longitude"])

    def test_svg_image_is_dropped(self):
        # pageimages가 로고·문장·지도 SVG를 대표 이미지로 주는 경우가 있어 사진만 남긴다.
        page = {"pageid": 7, "title": "어떤 군", "original": {"source": f"{_COMMONS}/Emblem.svg"}}
        self.assertEqual(wikimedia._normalize_page(page)["first_image"], "")

    def test_logo_and_map_images_are_dropped_by_filename(self):
        # pageimages가 사진 대신 로고·지도를 대표 이미지로 주는 경우가 있다.
        for filename in ("Seoultech_LOGO.png", "Locator_map_of_Seoul.png", "Flag_of_Busan.png"):
            page = {"pageid": 7, "title": "어떤 대학", "original": {"source": f"{_COMMONS}/{filename}"}}
            self.assertEqual(wikimedia._normalize_page(page)["first_image"], "", filename)

    def test_non_commons_fair_use_image_is_dropped(self):
        # upload.wikimedia.org/wikipedia/ko/ 는 한국어 위키백과에 개별 업로드된 공정 이용
        # 파일이라 위키백과 밖에서는 못 쓴다 — 버린다.
        page = {
            "pageid": 7,
            "title": "광안리해수욕장",
            "original": {"source": "https://upload.wikimedia.org/wikipedia/ko/b/b9/P080713002.jpg"},
        }
        self.assertEqual(wikimedia._normalize_page(page)["first_image"], "")


class EnrichFromWikimediaTest(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882")
        )

    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_fills_blank_photo_url_and_records_pageid(self, mock_search):
        mock_search.return_value = [
            _candidate("남산서울타워", lat=37.5512, lng=126.9882, content_id="98765")
        ]
        status, url = enrich_place_photo_from_wikimedia(self.place)

        self.assertEqual(status, "matched")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, url)
        self.assertTrue(
            PlaceSource.objects.filter(
                place=self.place, source=WIKIMEDIA_SOURCE, source_id="98765"
            ).exists()
        )

    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_no_match_records_no_match_and_is_not_searched_again(self, mock_search):
        mock_search.return_value = [_candidate("전혀 다른 문서")]
        status, _ = enrich_place_photo_from_wikimedia(self.place)
        self.assertEqual(status, "no_match")

        status, _ = enrich_place_photo_from_wikimedia(self.place)
        self.assertEqual(status, "no_match")
        mock_search.assert_called_once()  # 두 번째 호출은 재검색하지 않는다

    @patch("places.place_photo_enrichment.wikimedia.get_detail")
    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_known_pageid_skips_search_and_uses_get_detail(self, mock_search, mock_detail):
        PlaceSource.objects.create(place=self.place, source=WIKIMEDIA_SOURCE, source_id="98765")
        mock_detail.return_value = _candidate("남산서울타워") | {
            "first_image": "https://upload.wikimedia.org/updated.jpg"
        }

        status, _ = enrich_place_photo_from_wikimedia(self.place)

        mock_search.assert_not_called()
        mock_detail.assert_called_once_with("98765")
        self.assertEqual(status, "matched")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, "https://upload.wikimedia.org/updated.jpg")

    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_keeps_existing_photo_url_without_overwrite(self, mock_search):
        self.place.photo_url = "https://admin-set.example/photo.jpg"
        self.place.save(update_fields=["photo_url"])
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        status, _ = enrich_place_photo_from_wikimedia(self.place)

        self.assertEqual(status, "matched_no_change")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, "https://admin-set.example/photo.jpg")


class ImportPlacePhotosWikimediaCommandTest(TestCase):
    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_default_run_skips_tour_api_filled_and_already_tried_places(self, mock_search):
        # TourAPI가 이미 채운 명소 — photo_url이 비어 있지 않으니 대상이 아니다.
        tour_filled = Place.objects.create(
            name="협재해수욕장", latitude=Decimal("33.39"), longitude=Decimal("126.24"),
            photo_url="https://tong.visitkorea.or.kr/x.jpg",
        )
        # TourAPI가 못 찾은 명소 — photo_url이 비어 있으니 위키백과가 이어서 시도한다.
        tour_no_match = Place.objects.create(
            name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882")
        )
        PlaceSource.objects.create(
            place=tour_no_match, source=TOUR_API_SOURCE, source_id=f"__no_match__{tour_no_match.id}"
        )
        # 위키백과를 이미 시도한 명소 — 다시 검색하지 않는다.
        wiki_tried = Place.objects.create(name="이미함", latitude=Decimal("37.5"), longitude=Decimal("127.0"))
        PlaceSource.objects.create(
            place=wiki_tried, source=WIKIMEDIA_SOURCE, source_id=f"__no_match__{wiki_tried.id}"
        )
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        call_command("import_place_photos_wikimedia", "--sleep", "0")

        searched = [c.args[0] for c in mock_search.call_args_list]
        self.assertEqual(searched, ["남산서울타워"])
        tour_filled.refresh_from_db()
        self.assertEqual(tour_filled.photo_url, "https://tong.visitkorea.or.kr/x.jpg")

    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_dry_run_does_not_save(self, mock_search):
        place = Place.objects.create(
            name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882")
        )
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        call_command("import_place_photos_wikimedia", "--dry-run", "--sleep", "0")

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "")
        self.assertFalse(PlaceSource.objects.filter(source=WIKIMEDIA_SOURCE).exists())

    @patch("places.place_photo_enrichment.wikimedia.search_keyword")
    def test_command_stops_after_consecutive_errors(self, mock_search):
        for i in range(8):
            Place.objects.create(
                name=f"장소{i}", latitude=Decimal("37.5"), longitude=Decimal(f"127.{i}")
            )
        mock_search.side_effect = RuntimeError("Read timed out")

        call_command("import_place_photos_wikimedia", "--sleep", "0")

        self.assertEqual(mock_search.call_count, 5)  # 5건 연속 실패하면 멈춘다

    @patch("places.place_photo_enrichment.wikimedia.get_detail")
    def test_command_pins_page_id_with_place_id(self, mock_detail):
        place = Place.objects.create(name="어느 카페", latitude=Decimal("37.5"), longitude=Decimal("127.0"))
        mock_detail.return_value = _candidate("어느 카페") | {
            "first_image": "https://upload.wikimedia.org/pinned.jpg"
        }

        call_command("import_place_photos_wikimedia", "--place-id", str(place.id), "--page-id", "555000")

        self.assertTrue(
            PlaceSource.objects.filter(
                place=place, source=WIKIMEDIA_SOURCE, source_id="555000"
            ).exists()
        )
        place.refresh_from_db()
        self.assertEqual(place.photo_url, "https://upload.wikimedia.org/pinned.jpg")

    def test_page_id_without_place_id_errors(self):
        with self.assertRaises(Exception):
            call_command("import_place_photos_wikimedia", "--page-id", "123")
