"""feature/be/place-photo: TourAPI로 명소(Place) 대표 사진(photo_url) 보강.

- 이름이 정확히 일치하고 좌표가 가까운 관광정보만 인정하는지 (pick_photo_match)
- 비어 있는 photo_url만 채우고 관리자 값은 지키는지 (enrich_place_photo)
- 매칭한 content_id를 PlaceSource(TOUR_API)에 남기고, 재실행 때 재검색 대신 그 id로 조회하는지
- 일일 한도 초과면 실행을 멈추는지
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from places.models import Place, PlaceSource
from places.place_photo_enrichment import (
    TOUR_API_SOURCE,
    enrich_place_photo,
    normalize_name_for_match,
    pick_photo_match,
)
from places.sources import tour_api


def _candidate(title, *, image="https://tong.visitkorea.or.kr/a.jpg", lat=37.5665, lng=126.9780):
    return {
        "content_id": "1",
        "content_type_id": "12",
        "title": title,
        "address": "서울특별시 중구",
        "latitude": lat,
        "longitude": lng,
        "first_image": image,
    }


class NormalizeNameTest(TestCase):
    def test_strips_spaces_parens_and_casefolds(self):
        self.assertEqual(normalize_name_for_match("카페 그루비"), normalize_name_for_match("카페그루비"))
        self.assertEqual(normalize_name_for_match("The Coffee"), normalize_name_for_match("the coffee"))

    def test_empty_stays_empty(self):
        self.assertEqual(normalize_name_for_match(""), "")
        self.assertEqual(normalize_name_for_match(None), "")


class PickPhotoMatchTest(TestCase):
    def test_exact_name_and_near_coords_is_picked(self):
        place = Place(name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882"))
        candidates = [_candidate("남산서울타워", lat=37.5512, lng=126.9883)]
        match = pick_photo_match(place, candidates)
        self.assertEqual(match["first_image"], "https://tong.visitkorea.or.kr/a.jpg")

    def test_same_name_but_far_coords_is_rejected(self):
        place = Place(name="스타벅스", latitude=Decimal("37.5665"), longitude=Decimal("126.9780"))
        candidates = [_candidate("스타벅스", lat=35.1796, lng=129.0756)]  # 부산
        self.assertIsNone(pick_photo_match(place, candidates))

    def test_partial_name_is_not_accepted(self):
        place = Place(name="그루비", latitude=Decimal("37.5665"), longitude=Decimal("126.9780"))
        candidates = [_candidate("카페 그루비", lat=37.5665, lng=126.9780)]
        self.assertIsNone(pick_photo_match(place, candidates))

    def test_candidate_without_image_is_ignored(self):
        place = Place(name="어떤명소", latitude=Decimal("37.5665"), longitude=Decimal("126.9780"))
        candidates = [_candidate("어떤명소", image="")]
        self.assertIsNone(pick_photo_match(place, candidates))

    def test_no_coords_and_conflicting_images_is_ambiguous(self):
        place = Place(name="스타벅스")  # 좌표 없음
        candidates = [
            _candidate("스타벅스", image="https://tong.visitkorea.or.kr/a.jpg"),
            _candidate("스타벅스", image="https://tong.visitkorea.or.kr/b.jpg"),
        ]
        self.assertIsNone(pick_photo_match(place, candidates))

    def test_nearest_candidate_wins(self):
        place = Place(name="한옥마을", latitude=Decimal("37.5665"), longitude=Decimal("126.9780"))
        candidates = [
            _candidate("한옥마을", image="https://far.jpg", lat=37.5680, lng=126.9795),
            _candidate("한옥마을", image="https://near.jpg", lat=37.5666, lng=126.9781),
        ]
        match = pick_photo_match(place, candidates)
        self.assertEqual(match["first_image"], "https://near.jpg")


class EnrichPlacePhotoTest(TestCase):
    def setUp(self):
        self.place = Place.objects.create(
            name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882")
        )

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_fills_blank_photo_url(self, mock_search):
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]
        status, url = enrich_place_photo(self.place)
        self.assertEqual(status, "matched")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, url)

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_keeps_existing_photo_url_without_overwrite(self, mock_search):
        self.place.photo_url = "https://admin-set.example/photo.jpg"
        self.place.save(update_fields=["photo_url"])
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        status, url = enrich_place_photo(self.place)
        self.assertEqual(status, "matched_no_change")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, "https://admin-set.example/photo.jpg")

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_overwrite_replaces_existing(self, mock_search):
        self.place.photo_url = "https://admin-set.example/photo.jpg"
        self.place.save(update_fields=["photo_url"])
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        status, url = enrich_place_photo(self.place, overwrite=True)
        self.assertEqual(status, "matched")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, url)

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_no_match_leaves_photo_url_but_records_no_match(self, mock_search):
        mock_search.return_value = [_candidate("전혀다른곳")]
        status, url = enrich_place_photo(self.place)
        self.assertEqual(status, "no_match")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, "")
        src = PlaceSource.objects.get(place=self.place, source=TOUR_API_SOURCE)
        self.assertTrue(src.source_id.startswith("__no_match__"))

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_recorded_no_match_is_not_searched_again(self, mock_search):
        PlaceSource.objects.create(
            place=self.place, source=TOUR_API_SOURCE, source_id=f"__no_match__{self.place.id}"
        )
        status, url = enrich_place_photo(self.place)
        self.assertEqual(status, "no_match")
        mock_search.assert_not_called()

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_overwrite_retries_recorded_no_match(self, mock_search):
        PlaceSource.objects.create(
            place=self.place, source=TOUR_API_SOURCE, source_id=f"__no_match__{self.place.id}"
        )
        mock_search.return_value = [
            _candidate("남산서울타워", lat=37.5512, lng=126.9882) | {"content_id": "555"}
        ]
        status, url = enrich_place_photo(self.place, overwrite=True)
        self.assertEqual(status, "matched")
        mock_search.assert_called_once()
        self.assertTrue(
            PlaceSource.objects.filter(place=self.place, source=TOUR_API_SOURCE, source_id="555").exists()
        )
        self.assertFalse(
            PlaceSource.objects.filter(source_id=f"__no_match__{self.place.id}").exists()
        )

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_match_records_tour_api_placesource(self, mock_search):
        mock_search.return_value = [
            _candidate("남산서울타워", lat=37.5512, lng=126.9882) | {"content_id": "126508"}
        ]
        enrich_place_photo(self.place)
        self.assertTrue(
            PlaceSource.objects.filter(
                place=self.place, source=TOUR_API_SOURCE, source_id="126508"
            ).exists()
        )

    @patch("places.place_photo_enrichment.tour_api.get_detail")
    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_known_placesource_skips_search_and_uses_get_detail(self, mock_search, mock_detail):
        PlaceSource.objects.create(place=self.place, source=TOUR_API_SOURCE, source_id="126508")
        mock_detail.return_value = _candidate("남산서울타워", lat=37.5512, lng=126.9882) | {
            "first_image": "https://tong.visitkorea.or.kr/updated.jpg"
        }

        status, url = enrich_place_photo(self.place)

        mock_search.assert_not_called()
        mock_detail.assert_called_once_with("126508")
        self.assertEqual(status, "matched")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, "https://tong.visitkorea.or.kr/updated.jpg")


class ImportPlacePhotosCommandTest(TestCase):
    @patch("places.management.commands.import_place_photos.tour_api.search_keyword")
    def test_command_swallows_per_row_errors_and_continues(self, mock_search):
        good = Place.objects.create(
            name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882")
        )
        Place.objects.create(name="폭탄", latitude=Decimal("37.0"), longitude=Decimal("127.0"))

        def side_effect(keyword):
            if keyword == "폭탄":
                raise RuntimeError("TourAPI 오류: 22 LIMITED_NUMBER_OF_SERVICE_REQUESTS")
            return [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        mock_search.side_effect = side_effect
        call_command("import_place_photos")

        good.refresh_from_db()
        self.assertTrue(good.photo_url)

    @patch("places.management.commands.import_place_photos.tour_api.search_keyword")
    def test_dry_run_does_not_save(self, mock_search):
        place = Place.objects.create(
            name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882")
        )
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]
        call_command("import_place_photos", "--dry-run")

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "")

    @patch("places.place_photo_enrichment.tour_api.get_detail")
    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_default_run_skips_already_tried_places(self, mock_search, mock_detail):
        done = Place.objects.create(name="이미함", latitude=Decimal("37.5"), longitude=Decimal("127.0"))
        PlaceSource.objects.create(place=done, source=TOUR_API_SOURCE, source_id=f"__no_match__{done.id}")
        fresh = Place.objects.create(name="남산서울타워", latitude=Decimal("37.5512"), longitude=Decimal("126.9882"))
        mock_search.return_value = [_candidate("남산서울타워", lat=37.5512, lng=126.9882)]

        call_command("import_place_photos", "--sleep", "0")

        # 이미 시도한 명소는 다시 검색하지 않는다.
        searched = [c.args[0] for c in mock_search.call_args_list]
        self.assertNotIn("이미함", searched)
        self.assertIn("남산서울타워", searched)

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_name_contains_only_processes_matching_names(self, mock_search):
        beach = Place.objects.create(
            name="협재해수욕장", latitude=Decimal("33.39"), longitude=Decimal("126.24")
        )
        park = Place.objects.create(
            name="올림픽공원", latitude=Decimal("37.52"), longitude=Decimal("127.12")
        )
        cafe = Place.objects.create(
            name="바다뷰 카페", latitude=Decimal("33.40"), longitude=Decimal("126.25")
        )
        mock_search.return_value = []

        call_command("import_place_photos", "--name-contains", "해수욕장,공원", "--sleep", "0")

        searched = [c.args[0] for c in mock_search.call_args_list]
        self.assertIn("협재해수욕장", searched)
        self.assertIn("올림픽공원", searched)
        self.assertNotIn("바다뷰 카페", searched)

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_command_stops_after_consecutive_errors(self, mock_search):
        for i in range(8):
            Place.objects.create(
                name=f"장소{i}", latitude=Decimal("37.5"), longitude=Decimal(f"127.{i}")
            )
        mock_search.side_effect = RuntimeError("Read timed out")

        call_command("import_place_photos", "--sleep", "0")

        # 5건 연속 실패하면 멈춘다 (8건 전부 시도하지 않는다).
        self.assertEqual(mock_search.call_count, 5)

    @patch("places.place_photo_enrichment.tour_api.search_keyword")
    def test_command_stops_on_daily_limit(self, mock_search):
        first = Place.objects.create(name="가장소", latitude=Decimal("37.5"), longitude=Decimal("127.0"))
        second = Place.objects.create(name="나장소", latitude=Decimal("37.6"), longitude=Decimal("127.1"))
        mock_search.side_effect = tour_api.TourApiDailyLimitError("일일 한도 초과")

        call_command("import_place_photos")

        self.assertEqual(mock_search.call_count, 1)  # id 순, 첫 건에서 멈춤
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(first.photo_url, "")
        self.assertEqual(second.photo_url, "")

    @patch("places.place_photo_enrichment.tour_api.get_detail")
    def test_command_pins_content_id_with_place_id(self, mock_detail):
        place = Place.objects.create(name="어느 카페", latitude=Decimal("37.5"), longitude=Decimal("127.0"))
        mock_detail.return_value = _candidate("어느 카페") | {
            "first_image": "https://tong.visitkorea.or.kr/pinned.jpg"
        }

        call_command("import_place_photos", "--place-id", str(place.id), "--content-id", "999888")

        self.assertTrue(
            PlaceSource.objects.filter(
                place=place, source=TOUR_API_SOURCE, source_id="999888"
            ).exists()
        )
        place.refresh_from_db()
        self.assertEqual(place.photo_url, "https://tong.visitkorea.or.kr/pinned.jpg")
