"""Phase 2-1 (place, work data) checklist tests. See docs/PHASES/PHASE2.md 2-1."""

import io
import json
import os
import tempfile
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from places.management.commands.import_places import Command as ImportPlacesCommand
from places.models import Place, PlaceSource, PlaceTranslation, PlaceWork, Work, WorkTranslation
from places.services import haversine_distance_meters

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
SAMPLE_V1 = os.path.join(SAMPLE_DIR, "sample_places_v1.json")
SAMPLE_V2 = os.path.join(SAMPLE_DIR, "sample_places_v2.json")


def run_import(file_path, source="TEST_SOURCE"):
    out = io.StringIO()
    call_command("import_places", file=file_path, source=source, stdout=out)
    return out.getvalue()


def write_json(items):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
    return path


def create_place_with_source(name, source, source_id, **extra):
    place = Place.objects.create(name=name, **extra)
    PlaceSource.objects.create(place=place, source=source, source_id=source_id)
    return place


def get_place_by_source(source, source_id):
    return Place.objects.get(sources__source=source, sources__source_id=source_id)


class ImportCreatesPlacesTest(TestCase):
    """checklist 1: import from local json actually fills real data."""

    def test_import_creates_places_with_real_fields(self):
        output = run_import(SAMPLE_V1)

        self.assertEqual(Place.objects.count(), 3)

        gyeongbokgung = get_place_by_source("TEST_SOURCE", "A001")
        self.assertEqual(gyeongbokgung.name, "경복궁")
        self.assertEqual(gyeongbokgung.address, "서울특별시 종로구 사직로 161")
        self.assertEqual(gyeongbokgung.latitude, Decimal("37.579617"))
        self.assertEqual(gyeongbokgung.longitude, Decimal("126.977041"))

        namsan = get_place_by_source("TEST_SOURCE", "A002")
        self.assertEqual(namsan.name, "남산타워")
        self.assertEqual(namsan.latitude, Decimal("37.5512"))

        self.assertIn("새로 만듦 3건", output)

    def test_import_skips_items_without_source_id(self):
        run_import(SAMPLE_V1)
        self.assertFalse(Place.objects.filter(name="원본번호없는명소").exists())

    def test_import_handles_non_numeric_coordinates(self):
        output = run_import(SAMPLE_V1)
        no_coord_place = get_place_by_source("TEST_SOURCE", "A003")
        self.assertEqual(no_coord_place.name, "좌표없는명소")
        self.assertIsNone(no_coord_place.latitude)
        self.assertIsNone(no_coord_place.longitude)
        self.assertIn("좌표 파싱 실패 1건", output)


class ImportNoDuplicatesTest(TestCase):
    """checklist 2: importing the same data twice does not duplicate places."""

    def test_importing_same_file_twice_does_not_duplicate(self):
        run_import(SAMPLE_V1)
        count_after_first = Place.objects.count()

        run_import(SAMPLE_V1)
        count_after_second = Place.objects.count()

        self.assertEqual(count_after_first, count_after_second)
        self.assertEqual(
            PlaceSource.objects.filter(source="TEST_SOURCE", source_id="A001").count(), 1
        )

    def test_reimport_updates_instead_of_duplicating(self):
        run_import(SAMPLE_V1)
        run_import(SAMPLE_V2)

        self.assertEqual(
            PlaceSource.objects.filter(source="TEST_SOURCE", source_id="A001").count(), 1
        )
        updated = get_place_by_source("TEST_SOURCE", "A001")
        self.assertEqual(updated.name, "경복궁(수정됨)")


class AdminFieldsSurviveReimportTest(TestCase):
    """checklist 3: admin-filled scene description/photo survive reimport."""

    def test_admin_filled_description_and_photo_survive_reimport(self):
        run_import(SAMPLE_V1)

        place = get_place_by_source("TEST_SOURCE", "A001")
        place.description = "관리자가 직접 쓴 장면 설명"
        place.photo_url = "https://example.com/photo.jpg"
        place.business_hours = "09:00 ~ 18:00"
        place.save()

        run_import(SAMPLE_V2)

        place.refresh_from_db()
        self.assertEqual(place.description, "관리자가 직접 쓴 장면 설명")
        self.assertEqual(place.photo_url, "https://example.com/photo.jpg")
        self.assertEqual(place.business_hours, "09:00 ~ 18:00")
        self.assertEqual(place.name, "경복궁(수정됨)")

    def test_reimport_with_missing_field_does_not_blank_existing_value(self):
        run_import(SAMPLE_V1)
        namsan_before = get_place_by_source("TEST_SOURCE", "A002")
        self.assertEqual(namsan_before.address, "서울특별시 용산구 남산공원길 105")
        self.assertEqual(namsan_before.latitude, Decimal("37.5512"))

        run_import(SAMPLE_V2)

        namsan_after = get_place_by_source("TEST_SOURCE", "A002")
        self.assertEqual(namsan_after.address, "서울특별시 용산구 남산공원길 105")
        self.assertEqual(namsan_after.latitude, Decimal("37.5512"))
        self.assertEqual(namsan_after.longitude, Decimal("126.9882"))


class PlaceWorkRelationTest(TestCase):
    """checklist 4: one place can link many works, one work can link many places."""

    def test_one_place_can_have_multiple_works(self):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "P1")
        work1 = Work.objects.create(title="작품A", category=Work.Category.DRAMA)
        work2 = Work.objects.create(title="작품B", category=Work.Category.MOVIE)

        PlaceWork.objects.create(place=place, work=work1, scene_description="작품A의 왕궁 장면")
        PlaceWork.objects.create(place=place, work=work2, scene_description="작품B의 추격 장면")

        self.assertEqual(place.place_works.count(), 2)
        descriptions = set(place.place_works.values_list("scene_description", flat=True))
        self.assertEqual(descriptions, {"작품A의 왕궁 장면", "작품B의 추격 장면"})

    def test_one_work_can_have_multiple_places(self):
        work = Work.objects.create(title="작품C", category=Work.Category.DRAMA)
        place1 = create_place_with_source("경복궁", "TEST_SOURCE", "P2")
        place2 = create_place_with_source("남산타워", "TEST_SOURCE", "P3")

        PlaceWork.objects.create(place=place1, work=work, scene_description="1화 장면")
        PlaceWork.objects.create(place=place2, work=work, scene_description="2화 장면")

        self.assertEqual(work.place_works.count(), 2)
        self.assertEqual(
            set(work.place_works.values_list("place__name", flat=True)),
            {"경복궁", "남산타워"},
        )

    def test_same_place_and_work_cannot_be_linked_twice(self):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "P4")
        work = Work.objects.create(title="작품D", category=Work.Category.MOVIE)
        PlaceWork.objects.create(place=place, work=work, scene_description="첫 장면")

        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlaceWork.objects.create(place=place, work=work, scene_description="중복 장면")


class TranslationSlotTest(TestCase):
    """checklist 5: translation slots exist (can be empty for now)."""

    def test_place_translation_slot_exists_and_can_be_empty(self):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "P5")
        self.assertEqual(place.translations.count(), 0)

    def test_place_translation_can_be_filled_in(self):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "P6")
        translation = PlaceTranslation.objects.create(
            place=place, language="en", name="Gyeongbokgung", description="A royal palace"
        )
        self.assertEqual(place.translations.count(), 1)
        self.assertEqual(translation.language, "en")

    def test_work_translation_slot_exists_and_can_be_filled_in(self):
        work = Work.objects.create(title="작품E", category=Work.Category.DRAMA)
        self.assertEqual(work.translations.count(), 0)

        translation = WorkTranslation.objects.create(work=work, language="ja", title="Sakuhin E")
        self.assertEqual(work.translations.count(), 1)
        self.assertEqual(translation.title, "Sakuhin E")

    def test_same_place_language_pair_cannot_be_duplicated(self):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "P7")
        PlaceTranslation.objects.create(place=place, language="en", name="Gyeongbokgung")

        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlaceTranslation.objects.create(place=place, language="en", name="Duplicate")


class PlaceSourceTest(TestCase):
    """한 명소가 여러 출처를 가질 수 있는지, 같은 출처+원본번호는 중복될 수 없는지 확인."""

    def test_one_place_can_have_multiple_sources(self):
        place = create_place_with_source("경복궁", "KCISA", "K1")
        PlaceSource.objects.create(place=place, source="GG_DATA_DREAM", source_id="G1")

        self.assertEqual(place.sources.count(), 2)
        self.assertEqual(
            set(place.sources.values_list("source", flat=True)),
            {"KCISA", "GG_DATA_DREAM"},
        )

    def test_same_source_and_source_id_cannot_be_duplicated(self):
        create_place_with_source("경복궁", "KCISA", "K1")
        other_place = Place.objects.create(name="다른이름")

        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlaceSource.objects.create(place=other_place, source="KCISA", source_id="K1")


class HaversineDistanceTest(TestCase):
    """거리 계산 헬퍼가 100m 기준을 정확히 구분하는지 확인 (서울시청 좌표 기준)."""

    SEOUL_CITY_HALL = (37.566295, 126.977945)

    def test_same_point_is_zero_distance(self):
        lat, lng = self.SEOUL_CITY_HALL
        self.assertAlmostEqual(haversine_distance_meters(lat, lng, lat, lng), 0, places=3)

    def test_point_within_100m_is_under_threshold(self):
        lat, lng = self.SEOUL_CITY_HALL
        # 위도 0.0005도 차이는 대략 55m 정도.
        distance = haversine_distance_meters(lat, lng, lat + 0.0005, lng)
        self.assertLess(distance, 100)

    def test_point_beyond_100m_is_over_threshold(self):
        lat, lng = self.SEOUL_CITY_HALL
        # 위도 0.002도 차이는 대략 220m 정도.
        distance = haversine_distance_meters(lat, lng, lat + 0.002, lng)
        self.assertGreater(distance, 100)


class ImportEdgeCaseHelperTest(TestCase):
    """import_places helper edge cases: missing value / odd format / partial fields."""

    def setUp(self):
        self.command = ImportPlacesCommand()

    def test_get_source_id_missing_key_returns_empty_string(self):
        self.assertEqual(self.command._get_source_id({}), "")

    def test_get_source_id_none_value_returns_empty_string(self):
        self.assertEqual(self.command._get_source_id({"id": None}), "")

    def test_get_source_id_empty_string_returns_empty_string(self):
        self.assertEqual(self.command._get_source_id({"id": ""}), "")

    def test_to_decimal_none_is_treated_as_success_with_none_value(self):
        value, ok = self.command._to_decimal(None)
        self.assertIsNone(value)
        self.assertTrue(ok)

    def test_to_decimal_empty_string_is_treated_as_success_with_none_value(self):
        value, ok = self.command._to_decimal("")
        self.assertIsNone(value)
        self.assertTrue(ok)

    def test_to_decimal_non_numeric_string_fails(self):
        value, ok = self.command._to_decimal("정보없음")
        self.assertIsNone(value)
        self.assertFalse(ok)

    def test_parse_place_fields_with_only_some_fields_present(self):
        fields, coord_failed = self.command._parse_place_fields({"장소명": "이름만있음"})
        self.assertEqual(fields["name"], "이름만있음")
        self.assertEqual(fields["address"], "")
        self.assertIsNone(fields["latitude"])
        self.assertIsNone(fields["longitude"])
        self.assertFalse(coord_failed)

    def test_import_missing_file_raises_command_error(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("import_places", file="no_such_file.json", source="TEST_SOURCE")

    def test_import_invalid_json_raises_command_error(self):
        from django.core.management.base import CommandError

        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("this is not json {{{")
        try:
            with self.assertRaises(CommandError):
                call_command("import_places", file=path, source="TEST_SOURCE")
        finally:
            os.remove(path)

    def test_import_with_null_and_empty_field_values_does_not_crash(self):
        path = write_json(
            [
                {"고유번호": "N1", "장소명": None, "소재지": "", "위도": None, "경도": ""},
            ]
        )
        try:
            run_import(path)
        finally:
            os.remove(path)

        place = get_place_by_source("TEST_SOURCE", "N1")
        self.assertEqual(place.name, "")
        self.assertEqual(place.address, "")
        self.assertIsNone(place.latitude)
        self.assertIsNone(place.longitude)
