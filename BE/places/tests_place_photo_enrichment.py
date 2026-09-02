"""feature/be/place-photo-insert: TourAPI로 명소(Place) 대표 사진(photo_url) 보강.

- 이름이 정확히 일치하고 좌표가 가까운 관광정보만 인정하는지 (pick_photo_match)
- 비어 있는 photo_url만 채우고 관리자 값은 지키는지 (enrich_place_photo)
- 못 찾은 명소는 손대지 않는지
- 커맨드가 건별 오류를 삼키고 끝까지 도는지
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from places.models import Place
from places.place_photo_enrichment import (
    enrich_place_photo,
    normalize_name_for_match,
    pick_photo_match,
)


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
    def test_no_match_leaves_place_untouched(self, mock_search):
        mock_search.return_value = [_candidate("전혀다른곳")]
        status, url = enrich_place_photo(self.place)
        self.assertEqual(status, "no_match")
        self.place.refresh_from_db()
        self.assertEqual(self.place.photo_url, "")


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
