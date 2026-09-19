from importlib import import_module

from django.apps import apps
from django.test import TestCase

from places.models import Place
from places.regions import extract_region


class ExtractRegionTests(TestCase):
    def test_full_name(self):
        self.assertEqual(extract_region("서울특별시 종로구 청와대로 1"), "서울특별시")
        self.assertEqual(extract_region("경기도 파주시 회동길 145"), "경기도")

    def test_short_name_is_normalized(self):
        self.assertEqual(extract_region("경기 파주시 회동길 145"), "경기도")
        self.assertEqual(extract_region("서울 마포구 월드컵로 137"), "서울특별시")
        self.assertEqual(extract_region("부산 해운대구 해운대해변로 264"), "부산광역시")
        self.assertEqual(extract_region("충남 태안군 안면읍"), "충청남도")

    def test_old_names_become_current_official_names(self):
        self.assertEqual(extract_region("강원도 강릉시 사천면"), "강원특별자치도")
        self.assertEqual(extract_region("전라북도 전주시 완산구"), "전북특별자치도")
        self.assertEqual(extract_region("제주도 서귀포시"), "제주특별자치도")

    def test_glued_address(self):
        self.assertEqual(extract_region("경기도고양시 일산동구"), "경기도")

    def test_gwangju_city_in_gyeonggi_is_not_gwangju_metropolitan(self):
        self.assertEqual(extract_region("광주시 곤지암읍"), "")
        self.assertEqual(extract_region("광주 북구 첨단과기로"), "광주광역시")

    def test_empty_or_unknown_returns_empty_string(self):
        self.assertEqual(extract_region(""), "")
        self.assertEqual(extract_region(None), "")
        self.assertEqual(extract_region("   "), "")
        self.assertEqual(extract_region("Seoul Jongno-gu"), "")

    def test_all_17_regions_are_reachable(self):
        samples = [
            "서울특별시 a", "부산광역시 a", "대구광역시 a", "인천광역시 a", "광주광역시 a",
            "대전광역시 a", "울산광역시 a", "세종특별자치시 a", "경기도 a", "강원특별자치도 a",
            "충청북도 a", "충청남도 a", "전북특별자치도 a", "전라남도 a", "경상북도 a",
            "경상남도 a", "제주특별자치도 a",
        ]
        self.assertEqual(len({extract_region(sample) for sample in samples}), 17)


class PlaceRegionSaveTests(TestCase):
    def test_region_is_filled_from_address_on_create(self):
        place = Place.objects.create(name="헤이리", address="경기 파주시 탄현면 헤이리로 98")
        place.refresh_from_db()
        self.assertEqual(place.region, "경기도")

    def test_region_follows_address_change(self):
        place = Place.objects.create(name="가", address="서울 종로구 청와대로 1")
        place.address = "부산광역시 해운대구 해운대해변로 264"
        place.save()
        place.refresh_from_db()
        self.assertEqual(place.region, "부산광역시")

    def test_region_is_saved_when_update_fields_has_address(self):
        place = Place.objects.create(name="가", address="서울 종로구 청와대로 1")
        place.address = "제주도 서귀포시"
        place.save(update_fields=["address"])
        place.refresh_from_db()
        self.assertEqual(place.region, "제주특별자치도")

    def test_unknown_address_gives_empty_region(self):
        place = Place.objects.create(name="가", address="")
        self.assertEqual(place.region, "")


class BackfillMigrationTests(TestCase):
    def test_fill_region_fills_existing_places(self):
        place = Place.objects.create(name="가", address="강원도 강릉시")
        Place.objects.filter(pk=place.pk).update(region="")

        migration = import_module("places.migrations.0017_place_region")
        migration.fill_region(apps, None)

        place.refresh_from_db()
        self.assertEqual(place.region, "강원특별자치도")
