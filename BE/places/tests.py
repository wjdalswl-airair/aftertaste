"""Phase 2-1 (place, work data) checklist tests. See docs/PHASES/PHASE2.md 2-1."""

import io
import json
import os
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from places.management.commands.import_places import Command as ImportPlacesCommand
from places.models import Place, PlaceSource, PlaceTranslation, PlaceWork, Work, WorkTranslation
from places.services import build_composite_source_id, haversine_distance_meters, save_place_from_source

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


class ImportPlacesDistanceMergeTest(TestCase):
    """import_places도 100m 거리 매칭을 타는지 확인 (services.save_place_from_source 재사용 회귀 테스트)."""

    def test_new_source_within_100m_merges_instead_of_duplicating(self):
        existing = create_place_with_source(
            "기존명소",
            "OTHER_SOURCE",
            "O1",
            address="기존주소",
            latitude=Decimal("37.579617"),
            longitude=Decimal("126.977041"),
        )
        path = write_json(
            [
                {
                    "고유번호": "NEW1",
                    "장소명": "다른이름",
                    "소재지": "다른주소",
                    "위도": "37.579617",
                    "경도": "126.977041",
                },
            ]
        )
        try:
            output = run_import(path, source="TEST_SOURCE")
        finally:
            os.remove(path)

        self.assertEqual(Place.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.name, "기존명소")
        self.assertEqual(existing.address, "기존주소")
        self.assertTrue(PlaceSource.objects.filter(place=existing, source="TEST_SOURCE", source_id="NEW1").exists())
        self.assertIn("병합 1건", output)


class SavePlaceFromSourceTest(TestCase):
    """places.services.save_place_from_source의 3단계 판단(원본번호 조회 → 100m 매칭 → 신규 생성)."""

    def test_known_source_id_updates_only_non_empty_fields(self):
        place = create_place_with_source("경복궁", "SRC", "1", address="옛주소")

        result_place, created, matched_by = save_place_from_source(
            source="SRC", source_id="1", name="경복궁(새이름)", address="", latitude=None, longitude=None
        )

        self.assertFalse(created)
        self.assertEqual(matched_by, "source_id")
        self.assertEqual(result_place.pk, place.pk)
        place.refresh_from_db()
        self.assertEqual(place.name, "경복궁(새이름)")
        self.assertEqual(place.address, "옛주소")

    def test_unknown_source_id_without_nearby_place_creates_new(self):
        place, created, matched_by = save_place_from_source(
            source="SRC", source_id="new-1", name="새명소", latitude=Decimal("37.1"), longitude=Decimal("127.1")
        )

        self.assertTrue(created)
        self.assertEqual(matched_by, "new")
        self.assertEqual(Place.objects.count(), 1)

    def test_unknown_source_id_with_nearby_place_attaches_source_without_overwriting_fields(self):
        existing = create_place_with_source(
            "기존명소",
            "OTHER_SOURCE",
            "O1",
            address="기존주소",
            latitude=Decimal("37.566295"),
            longitude=Decimal("126.977945"),
        )

        place, created, matched_by = save_place_from_source(
            source="NEW_SOURCE",
            source_id="N1",
            name="다른이름",
            address="다른주소",
            latitude=Decimal("37.566595"),
            longitude=Decimal("126.977945"),
        )

        self.assertFalse(created)
        self.assertEqual(matched_by, "distance")
        self.assertEqual(place.pk, existing.pk)
        self.assertEqual(Place.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.name, "기존명소")
        self.assertEqual(existing.address, "기존주소")
        self.assertEqual(
            PlaceSource.objects.filter(place=existing, source="NEW_SOURCE", source_id="N1").count(), 1
        )

    def test_create_only_fields_applied_only_when_creating(self):
        place, created, matched_by = save_place_from_source(
            source="SRC", source_id="biz-1", name="영업시간있는명소", create_only_fields={"business_hours": "09:00~18:00"}
        )

        self.assertTrue(created)
        self.assertEqual(place.business_hours, "09:00~18:00")

    def test_create_only_fields_ignored_on_source_id_match(self):
        place = create_place_with_source("경복궁", "SRC", "biz-2", business_hours="원래시간")

        save_place_from_source(
            source="SRC", source_id="biz-2", name="경복궁", create_only_fields={"business_hours": "새시간"}
        )

        place.refresh_from_db()
        self.assertEqual(place.business_hours, "원래시간")

    def test_create_only_fields_ignored_on_distance_match(self):
        existing = create_place_with_source(
            "경복궁",
            "OTHER_SOURCE",
            "O2",
            business_hours="원래시간",
            latitude=Decimal("37.566295"),
            longitude=Decimal("126.977945"),
        )

        save_place_from_source(
            source="NEW_SOURCE",
            source_id="N2",
            name="경복궁",
            latitude=Decimal("37.566295"),
            longitude=Decimal("126.977945"),
            create_only_fields={"business_hours": "새시간"},
        )

        existing.refresh_from_db()
        self.assertEqual(existing.business_hours, "원래시간")

    def test_empty_create_only_field_value_is_not_set(self):
        place, created, matched_by = save_place_from_source(
            source="SRC", source_id="biz-3", name="명소", create_only_fields={"business_hours": ""}
        )

        self.assertEqual(place.business_hours, "")


class BuildCompositeSourceIdTest(TestCase):
    """경기데이터드림처럼 원본에 고유번호가 없는 출처를 위한 합성 키 생성."""

    def test_same_inputs_produce_same_key(self):
        key1 = build_composite_source_id("고양시", "2022", "드라마", "작품A", "장소A")
        key2 = build_composite_source_id("고양시", "2022", "드라마", "작품A", "장소A")
        self.assertEqual(key1, key2)

    def test_different_field_produces_different_key(self):
        key1 = build_composite_source_id("고양시", "2022", "드라마", "작품A", "장소A")
        key2 = build_composite_source_id("고양시", "2022", "드라마", "작품A", "장소B")
        self.assertNotEqual(key1, key2)

    def test_none_is_treated_as_empty_string(self):
        key = build_composite_source_id("고양시", None, "드라마")
        self.assertEqual(key, "고양시||드라마")


def _fake_gg_fetch(page_index, page_size):
    pages = {
        1: {
            "total_count": 3,
            "items": [
                {
                    "sigun_nm": "고양시",
                    "potogrf_yy": "2022",
                    "potogrf_div_nm": "드라마",
                    "work_nm": "작품A",
                    "potogrf_plc_nm": "장소A",
                },
                {
                    "sigun_nm": "고양시",
                    "potogrf_yy": "2022",
                    "potogrf_div_nm": "드라마",
                    "work_nm": "작품B",
                    "potogrf_plc_nm": "",
                },
            ],
        },
        2: {
            "total_count": 3,
            "items": [
                {
                    "sigun_nm": "고양시",
                    "potogrf_yy": "2022",
                    "potogrf_div_nm": "드라마",
                    "work_nm": "작품C",
                    "potogrf_plc_nm": "장소C",
                },
            ],
        },
    }
    return pages[page_index]


def _fake_gg_search_place(query, size=1):
    if "장소A" in query:
        return [
            {
                "place_name": "장소A",
                "address_name": "경기도 고양시 장소A",
                "road_address_name": "경기도 고양시 장소A로 1",
                "latitude": 37.1,
                "longitude": 127.1,
                "category_name": "",
            }
        ]
    if "장소C" in query:
        return [
            {
                "place_name": "장소C",
                "address_name": "경기도 고양시 장소C",
                "road_address_name": "",
                "latitude": 37.9,
                "longitude": 127.9,
                "category_name": "",
            }
        ]
    return []


class ImportGyeonggiDataDreamCommandTest(TestCase):
    """경기 데이터 드림 명령어: 페이지네이션, 지오코딩 연동, 스킵 집계. 실제 네트워크 호출은 안 한다."""

    def _run(self, **options):
        out = io.StringIO()
        call_command("import_gyeonggi_data_dream", stdout=out, stderr=out, **options)
        return out.getvalue()

    @patch("places.management.commands.import_gyeonggi_data_dream.kakao_geocoding.search_place")
    @patch("places.management.commands.import_gyeonggi_data_dream.gyeonggi_data_dream.fetch_photography_support")
    def test_paginates_and_creates_places(self, mock_fetch, mock_search):
        mock_fetch.side_effect = _fake_gg_fetch
        mock_search.side_effect = _fake_gg_search_place

        output = self._run()

        self.assertEqual(Place.objects.count(), 2)
        self.assertIn("새로 만듦 2건", output)
        self.assertIn("장소명 없어서 건너뜀 1건", output)

        place_a = Place.objects.get(name="장소A")
        self.assertEqual(place_a.address, "경기도 고양시 장소A로 1")
        place_c = Place.objects.get(name="장소C")
        self.assertEqual(place_c.address, "경기도 고양시 장소C")

    @patch("places.management.commands.import_gyeonggi_data_dream.kakao_geocoding.search_place")
    @patch("places.management.commands.import_gyeonggi_data_dream.gyeonggi_data_dream.fetch_photography_support")
    def test_skips_when_geocoding_returns_no_results(self, mock_fetch, mock_search):
        mock_fetch.side_effect = _fake_gg_fetch
        mock_search.return_value = []

        output = self._run()

        self.assertEqual(Place.objects.count(), 0)
        self.assertIn("지오코딩 결과 없어서 건너뜀 2건", output)

    @patch("places.management.commands.import_gyeonggi_data_dream.kakao_geocoding.search_place")
    @patch("places.management.commands.import_gyeonggi_data_dream.gyeonggi_data_dream.fetch_photography_support")
    def test_rerunning_does_not_duplicate(self, mock_fetch, mock_search):
        mock_fetch.side_effect = _fake_gg_fetch
        mock_search.side_effect = _fake_gg_search_place

        self._run()
        count_after_first = Place.objects.count()
        self._run()
        count_after_second = Place.objects.count()

        self.assertEqual(count_after_first, count_after_second)

    @patch("places.management.commands.import_gyeonggi_data_dream.kakao_geocoding.search_place")
    @patch("places.management.commands.import_gyeonggi_data_dream.gyeonggi_data_dream.fetch_photography_support")
    def test_max_pages_cap_stops_without_hanging(self, mock_fetch, mock_search):
        mock_fetch.return_value = {
            "total_count": 999999,
            "items": [
                {
                    "sigun_nm": "고양시",
                    "potogrf_yy": "2022",
                    "potogrf_div_nm": "드라마",
                    "work_nm": "무한작품",
                    "potogrf_plc_nm": "무한장소",
                }
            ],
        }
        mock_search.return_value = []

        output = self._run(max_pages=3)

        self.assertEqual(mock_fetch.call_count, 3)
        self.assertIn("페이지 상한", output)


def _fake_kcisa_rows():
    return [
        {
            "sequence_no": "1",
            "media_type": "drama",
            "title": "제목1",
            "place_name": "카페1",
            "place_type": "cafe",
            "description": "설명1",
            "business_hours": "09:00~21:00",
            "break_time": "",
            "closed_days": "",
            "address": "경기도 고양시 1",
            "latitude": "37.1",
            "longitude": "127.1",
            "phone": "",
            "last_updated": "",
        },
        {
            "sequence_no": "",
            "media_type": "drama",
            "title": "제목2",
            "place_name": "연번없음",
            "place_type": "cafe",
            "description": "",
            "business_hours": "",
            "break_time": "",
            "closed_days": "",
            "address": "",
            "latitude": "",
            "longitude": "",
            "phone": "",
            "last_updated": "",
        },
        {
            "sequence_no": "3",
            "media_type": "drama",
            "title": "제목3",
            "place_name": "좌표이상함",
            "place_type": "cafe",
            "description": "",
            "business_hours": "10:00~20:00",
            "break_time": "",
            "closed_days": "",
            "address": "경기도 어딘가",
            "latitude": "정보없음",
            "longitude": "정보없음",
            "phone": "",
            "last_updated": "",
        },
    ]


class ImportKcisaCommandTest(TestCase):
    """한국문화정보원 CSV 명령어: business_hours는 생성 시에만 채워지고 그 뒤로는 보존된다."""

    def _run(self, file_path="dummy.csv"):
        out = io.StringIO()
        call_command("import_kcisa", file=file_path, stdout=out)
        return out.getvalue()

    @patch("places.management.commands.import_kcisa.kcisa_csv.parse_filming_locations")
    def test_creates_places_and_fills_business_hours_only_on_create(self, mock_parse):
        mock_parse.return_value = _fake_kcisa_rows()

        output = self._run()

        self.assertEqual(Place.objects.count(), 2)
        self.assertIn("새로 만듦 2건", output)
        self.assertIn("연번 없어서 건너뜀 1건", output)
        self.assertIn("좌표 파싱 실패 1건", output)

        cafe1 = get_place_by_source("KCISA", "1")
        self.assertEqual(cafe1.business_hours, "09:00~21:00")
        self.assertEqual(cafe1.description, "")

    @patch("places.management.commands.import_kcisa.kcisa_csv.parse_filming_locations")
    def test_reimport_does_not_overwrite_business_hours(self, mock_parse):
        mock_parse.return_value = _fake_kcisa_rows()
        self._run()

        changed_rows = _fake_kcisa_rows()
        changed_rows[0]["business_hours"] = "00:00~24:00"
        mock_parse.return_value = changed_rows
        self._run()

        cafe1 = get_place_by_source("KCISA", "1")
        self.assertEqual(cafe1.business_hours, "09:00~21:00")

    @patch("places.management.commands.import_kcisa.kcisa_csv.parse_filming_locations")
    def test_admin_edit_survives_reimport(self, mock_parse):
        mock_parse.return_value = _fake_kcisa_rows()
        self._run()

        cafe1 = get_place_by_source("KCISA", "1")
        cafe1.business_hours = "관리자가고침"
        cafe1.save()

        self._run()

        cafe1.refresh_from_db()
        self.assertEqual(cafe1.business_hours, "관리자가고침")

    @patch("places.management.commands.import_kcisa.kcisa_csv.parse_filming_locations")
    def test_missing_file_raises_command_error(self, mock_parse):
        from django.core.management.base import CommandError

        mock_parse.side_effect = FileNotFoundError()
        with self.assertRaises(CommandError):
            call_command("import_kcisa", file="no_such_file.csv")

    @patch("places.management.commands.import_kcisa.kcisa_csv.parse_filming_locations")
    def test_distance_match_does_not_overwrite_name_address_or_business_hours(self, mock_parse):
        existing = create_place_with_source(
            "기존카페",
            "GYEONGGI_DATA_DREAM",
            "G1",
            address="기존주소",
            business_hours="기존시간",
            latitude=Decimal("37.566295"),
            longitude=Decimal("126.977945"),
        )
        mock_parse.return_value = [
            {
                "sequence_no": "99",
                "place_name": "새이름",
                "address": "새주소",
                "business_hours": "새시간",
                "latitude": "37.566295",
                "longitude": "126.977945",
            },
        ]

        output = self._run()

        self.assertEqual(Place.objects.count(), 1)
        existing.refresh_from_db()
        self.assertEqual(existing.name, "기존카페")
        self.assertEqual(existing.address, "기존주소")
        self.assertEqual(existing.business_hours, "기존시간")
        self.assertIn("좌표 100m 이내 기존 명소와 병합 1건", output)


# ---------------------------------------------------------------------------
# Phase 2-3 (검색) checklist tests. See docs/PHASES/PHASE2.md 2-3,
# docs/DETAIL_SPEC.md 3-2.
# ---------------------------------------------------------------------------

from rest_framework import status
from rest_framework.test import APIClient

from accounts.firebase import InvalidFirebaseToken
from accounts.models import Member
from places.models import SearchHistory

SEARCH_URL = "/api/places/search/"
AUTOCOMPLETE_URL = "/api/places/search/autocomplete/"


def make_decoded_token(uid, provider="google.com"):
    return {
        "uid": uid,
        "email": "test@example.com",
        "name": "테스터",
        "picture": "http://example.com/pic.jpg",
        "firebase": {"sign_in_provider": provider},
    }


class SearchTestData(TestCase):
    """검색 테스트에서 공통으로 쓰는 명소/작품 데이터를 만든다."""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

        self.gyeongbokgung = create_place_with_source(
            "경복궁", "TEST_SOURCE", "SEARCH_S1", address="서울 종로구"
        )
        self.namsan = create_place_with_source(
            "남산타워", "TEST_SOURCE", "SEARCH_S2", address="서울 용산구"
        )

        self.drama_work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA)
        self.movie_work = Work.objects.create(title="극한직업", category=Work.Category.MOVIE)

        self.mixed_place = create_place_with_source(
            "경복궁야경투어", "TEST_SOURCE", "SEARCH_S3", address="서울 종로구"
        )
        self.mixed_work = Work.objects.create(title="경복궁의 비밀", category=Work.Category.DRAMA)


class SearchViewLoginNotRequiredTest(SearchTestData):
    """checklist: 로그인 없이 검색된다 / 무효 만료 토큰이어도 검색은 막히지 않는다."""

    def test_search_without_token_returns_200(self):
        response = self.client.get(SEARCH_URL, {"q": "경복궁"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("accounts.authentication.verify_id_token")
    def test_search_with_invalid_token_still_returns_results(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(SEARCH_URL, {"q": "경복궁"}, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        place_names = [p["name"] for p in response.data["places"]]
        self.assertIn("경복궁", place_names)

    @patch("accounts.authentication.verify_id_token")
    def test_search_with_expired_token_does_not_save_history(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        self.client.get(SEARCH_URL, {"q": "경복궁"}, **self.auth_header)

        self.assertEqual(SearchHistory.objects.count(), 0)


class SearchViewSectionTest(SearchTestData):
    """checklist: 결과가 명소 섹션과 작품 섹션으로 나뉘어 나온다."""

    def test_unified_search_splits_places_and_works(self):
        response = self.client.get(SEARCH_URL, {"q": "경복궁"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("places", response.data)
        self.assertIn("works", response.data)

        place_names = {p["name"] for p in response.data["places"]}
        work_titles = {w["title"] for w in response.data["works"]}

        self.assertIn("경복궁", place_names)
        self.assertIn("경복궁야경투어", place_names)
        self.assertIn("경복궁의 비밀", work_titles)
        self.assertNotIn("남산타워", place_names)
        self.assertNotIn("사랑비", work_titles)


class SearchViewTypeFilterTest(SearchTestData):
    """checklist: 드라마만, 영화만 골라 볼 수 있다."""

    def test_type_work_returns_all_works_without_places(self):
        response = self.client.get(SEARCH_URL, {"q": "사랑비", "type": "WORK"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["places"], [])
        titles = {w["title"] for w in response.data["works"]}
        self.assertIn("사랑비", titles)

    def test_type_drama_only_returns_drama(self):
        response = self.client.get(SEARCH_URL, {"q": "사랑비", "type": "DRAMA"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {w["title"] for w in response.data["works"]}
        self.assertIn("사랑비", titles)

    def test_type_drama_excludes_movie(self):
        response = self.client.get(SEARCH_URL, {"q": "극한직업", "type": "DRAMA"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["works"], [])
        self.assertEqual(response.data.get("message"), "검색결과가 존재하지 않습니다")

    def test_type_movie_only_returns_movie(self):
        response = self.client.get(SEARCH_URL, {"q": "극한직업", "type": "MOVIE"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {w["title"] for w in response.data["works"]}
        self.assertIn("극한직업", titles)

    def test_type_movie_excludes_drama(self):
        response = self.client.get(SEARCH_URL, {"q": "사랑비", "type": "MOVIE"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["works"], [])

    def test_invalid_type_value_returns_400(self):
        response = self.client.get(SEARCH_URL, {"q": "경복궁", "type": "ARTWORK"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SearchViewTypoTest(SearchTestData):
    """checklist: 오타를 내도 찾아진다. 완전히 다른 검색어로는 노이즈가 없어야 한다."""

    def test_typo_finds_correct_place(self):
        response = self.client.get(SEARCH_URL, {"q": "경보궁"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        place_names = {p["name"] for p in response.data["places"]}
        self.assertIn("경복궁", place_names)

    def test_missing_last_character_still_finds_place(self):
        response = self.client.get(SEARCH_URL, {"q": "남산타"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        place_names = {p["name"] for p in response.data["places"]}
        self.assertIn("남산타워", place_names)

    def test_completely_unrelated_keyword_returns_no_noise(self):
        response = self.client.get(SEARCH_URL, {"q": "쥐라기공원우주정거장"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["places"], [])
        self.assertEqual(response.data["works"], [])
        self.assertEqual(response.data.get("message"), "검색결과가 존재하지 않습니다")


class SearchViewNoResultTest(SearchTestData):
    """checklist: 결과가 없으면 검색결과가 존재하지 않습니다가 나온다."""

    def test_no_result_includes_message(self):
        response = self.client.get(SEARCH_URL, {"q": "존재하지않는검색어123"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "검색결과가 존재하지 않습니다")

    def test_result_found_has_no_message_key(self):
        response = self.client.get(SEARCH_URL, {"q": "경복궁"})

        self.assertNotIn("message", response.data)


class SearchViewEmptyKeywordTest(SearchTestData):
    """예외 상황: 검색어가 비어 있으면 검색하지 않는다."""

    def test_missing_q_param_returns_400(self):
        response = self.client.get(SEARCH_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_q_param_returns_400(self):
        response = self.client.get(SEARCH_URL, {"q": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_whitespace_only_q_param_returns_400(self):
        response = self.client.get(SEARCH_URL, {"q": "   "})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SearchViewTranslationTest(SearchTestData):
    """checklist: 저장된 번역 이름까지 같이 뒤진다."""

    def setUp(self):
        super().setUp()
        PlaceTranslation.objects.create(
            place=self.gyeongbokgung, language="en", name="Gyeongbokgung Palace"
        )
        WorkTranslation.objects.create(
            work=self.drama_work, language="en", title="Rain of Love"
        )

    def test_place_translation_name_is_searchable(self):
        response = self.client.get(SEARCH_URL, {"q": "Gyeongbokgung"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        place_names = {p["name"] for p in response.data["places"]}
        self.assertIn("경복궁", place_names)

    def test_work_translation_title_is_searchable(self):
        response = self.client.get(SEARCH_URL, {"q": "Rain of Love"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        work_titles = {w["title"] for w in response.data["works"]}
        self.assertIn("사랑비", work_titles)


class SearchAutocompleteTest(SearchTestData):
    """checklist: 글자를 치는 도중 후보가 나온다."""

    def test_autocomplete_returns_candidates_while_typing(self):
        response = self.client.get(AUTOCOMPLETE_URL, {"q": "경복"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("경복궁", response.data["suggestions"])
        self.assertIn("경복궁야경투어", response.data["suggestions"])
        self.assertIn("경복궁의 비밀", response.data["suggestions"])

    def test_autocomplete_empty_query_returns_empty_list_not_400(self):
        response = self.client.get(AUTOCOMPLETE_URL, {"q": ""})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["suggestions"], [])

    def test_autocomplete_missing_query_returns_empty_list_not_400(self):
        response = self.client.get(AUTOCOMPLETE_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["suggestions"], [])

    @patch("accounts.authentication.verify_id_token")
    def test_autocomplete_with_invalid_token_still_returns_candidates(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(AUTOCOMPLETE_URL, {"q": "경복"}, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("경복궁", response.data["suggestions"])

    def test_autocomplete_limits_to_ten_candidates(self):
        for i in range(15):
            create_place_with_source("자동완성명소" + str(i), "TEST_SOURCE", "AC_" + str(i))

        response = self.client.get(AUTOCOMPLETE_URL, {"q": "자동완성명소"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data["suggestions"]), 10)


class SearchHistoryTest(SearchTestData):
    """checklist: 로그인한 사람의 검색어가 서버에 쌓인다 / 비로그인은 남기지 않는다."""

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_user_search_is_saved_to_history(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="search-uid-1",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("search-uid-1")

        response = self.client.get(SEARCH_URL, {"q": "경복궁"}, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SearchHistory.objects.filter(member=member).count(), 1)
        self.assertEqual(SearchHistory.objects.get(member=member).keyword, "경복궁")

    def test_anonymous_user_search_is_not_saved(self):
        response = self.client.get(SEARCH_URL, {"q": "경복궁"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SearchHistory.objects.count(), 0)

    @patch("accounts.authentication.verify_id_token")
    def test_each_search_by_logged_in_user_creates_a_new_history_row(self, mock_verify):
        member = Member.objects.create(
            firebase_uid="search-uid-2",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("search-uid-2")

        self.client.get(SEARCH_URL, {"q": "경복궁"}, **self.auth_header)
        self.client.get(SEARCH_URL, {"q": "남산타워"}, **self.auth_header)

        self.assertEqual(SearchHistory.objects.filter(member=member).count(), 2)
        keywords = set(SearchHistory.objects.filter(member=member).values_list("keyword", flat=True))
        self.assertEqual(keywords, {"경복궁", "남산타워"})

    @patch("accounts.authentication.verify_id_token")
    def test_long_keyword_search_succeeds_and_history_is_truncated_to_200_chars(self, mock_verify):
        """검색어가 200자를 넘어도 검색은 전체 검색어로 되고, 이력에는 200자까지만 저장된다."""
        member = Member.objects.create(
            firebase_uid="search-uid-3",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )
        mock_verify.return_value = make_decoded_token("search-uid-3")

        long_keyword = "경복궁" + "가" * 300  # 200자를 훌쩍 넘는 검색어

        response = self.client.get(SEARCH_URL, {"q": long_keyword}, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        place_names = {p["name"] for p in response.data["places"]}
        self.assertIn("경복궁", place_names)  # 검색 자체는 전체 문자열로 정상 수행됨

        saved_keyword = SearchHistory.objects.get(member=member).keyword
        self.assertEqual(len(saved_keyword), 200)
        self.assertEqual(saved_keyword, long_keyword[:200])
