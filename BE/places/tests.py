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

    def test_autocomplete_shows_english_name_when_lang_and_approved(self):
        PlaceTranslation.objects.create(
            place=self.gyeongbokgung, language="en", name="Gyeongbokgung", is_approved=True
        )

        response = self.client.get(AUTOCOMPLETE_URL, {"q": "경복", "lang": "en"})

        self.assertIn("Gyeongbokgung", response.data["suggestions"])

    def test_autocomplete_shows_korean_name_without_lang(self):
        PlaceTranslation.objects.create(
            place=self.gyeongbokgung, language="en", name="Gyeongbokgung", is_approved=True
        )

        response = self.client.get(AUTOCOMPLETE_URL, {"q": "경복"})

        self.assertIn("경복궁", response.data["suggestions"])


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


POPULAR_URL = "/api/search/popular/"


class PopularKeywordsTest(TestCase):
    """추천(인기) 검색어: 최근 30일 검색 기록 집계 상위 5개 (DETAIL_SPEC 2-5, 6-1 #23)."""

    def setUp(self):
        self.client = APIClient()
        self.member = Member.objects.create(
            firebase_uid="popular-uid",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
        )

    def _add_history(self, keyword, times, days_ago=0):
        from datetime import timedelta

        from django.utils import timezone

        for _ in range(times):
            row = SearchHistory.objects.create(member=self.member, keyword=keyword)
            if days_ago:
                SearchHistory.objects.filter(pk=row.pk).update(
                    searched_at=timezone.now() - timedelta(days=days_ago)
                )

    def test_keywords_ordered_by_search_count_desc(self):
        self._add_history("도깨비", 3)
        self._add_history("경복궁", 1)
        self._add_history("사랑나무", 2)

        response = self.client.get(POPULAR_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["keywords"], ["도깨비", "사랑나무", "경복궁"])

    def test_single_search_keyword_is_included(self):
        self._add_history("한번만검색", 1)

        response = self.client.get(POPULAR_URL)

        self.assertIn("한번만검색", response.data["keywords"])

    def test_limited_to_five(self):
        for i in range(8):
            self._add_history(f"검색어{i}", i + 1)

        response = self.client.get(POPULAR_URL)

        self.assertEqual(len(response.data["keywords"]), 5)
        # 많이 검색된 순 → 검색어7(8회) ~ 검색어3(4회)
        self.assertEqual(response.data["keywords"][0], "검색어7")

    def test_searches_older_than_30_days_are_excluded(self):
        self._add_history("오래된검색어", 10, days_ago=40)
        self._add_history("최근검색어", 1)

        response = self.client.get(POPULAR_URL)

        self.assertEqual(response.data["keywords"], ["최근검색어"])

    def test_no_history_returns_empty_list_not_error(self):
        response = self.client.get(POPULAR_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["keywords"], [])

    def test_login_not_required(self):
        self._add_history("도깨비", 1)

        response = self.client.get(POPULAR_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_does_not_return_401(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")
        self._add_history("도깨비", 1)

        response = self.client.get(POPULAR_URL, HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Phase 2-4 (위치기반 추천 — 비로그인 분기만) checklist tests. See docs/PHASES/PHASE2.md 2-4.
# ---------------------------------------------------------------------------

RECOMMEND_URL = "/api/places/recommend/"

# 테스트 기준점: 서울시청 근처. 각 명소를 이 점에서 거리가 다르게 배치해 거리순 정렬을 검증한다.
BASE_LAT = 37.5665
BASE_LNG = 126.9780


class RecommendTestData(TestCase):
    """추천 테스트에서 공통으로 쓰는 클라이언트/헤더 준비."""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}


class RecommendationViewLoginNotRequiredTest(RecommendTestData):
    """checklist 1: 로그인 없이 추천이 나온다. 무효/만료 토큰이어도 막히지 않는다."""

    def setUp(self):
        super().setUp()
        create_place_with_source("명소1", "TEST_SOURCE", "REC_A1")
        create_place_with_source("명소2", "TEST_SOURCE", "REC_A2")

    def test_recommend_without_token_returns_200(self):
        response = self.client.get(RECOMMEND_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_recommend_response_has_places_key(self):
        response = self.client.get(RECOMMEND_URL)
        self.assertIn("places", response.data)

    @patch("accounts.authentication.verify_id_token")
    def test_recommend_with_invalid_token_still_returns_200_not_401(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(RECOMMEND_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("accounts.authentication.verify_id_token")
    def test_recommend_with_expired_token_still_returns_places(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(RECOMMEND_URL, **self.auth_header)

        self.assertGreater(len(response.data["places"]), 0)


class RecommendationViewNearestTest(RecommendTestData):
    """checklist 2: 위치 권한을 허용하면(lat/lng 유효) 주변 명소 3곳이 거리순으로 나온다."""

    def setUp(self):
        super().setUp()
        # 기준점에서 거리가 다른 4개 명소를 만든다. 가까운 순서: near < mid < far < farthest.
        self.near = create_place_with_source(
            "가까운명소", "TEST_SOURCE", "REC_NEAR", latitude=Decimal("37.5665"), longitude=Decimal("126.9780")
        )
        self.mid = create_place_with_source(
            "중간명소", "TEST_SOURCE", "REC_MID", latitude=Decimal("37.6000"), longitude=Decimal("126.9780")
        )
        self.far = create_place_with_source(
            "먼명소", "TEST_SOURCE", "REC_FAR", latitude=Decimal("37.7000"), longitude=Decimal("126.9780")
        )
        self.farthest = create_place_with_source(
            "가장먼명소", "TEST_SOURCE", "REC_FARTHEST", latitude=Decimal("38.0000"), longitude=Decimal("126.9780")
        )
        # 좌표 없는 명소는 거리 기준 추천 대상에서 빠져야 한다.
        self.no_coord = create_place_with_source("좌표없는명소", "TEST_SOURCE", "REC_NOCOORD")

    def test_nearest_places_returns_three_closest_in_distance_order(self):
        response = self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names, ["가까운명소", "중간명소", "먼명소"])

    def test_nearest_places_excludes_farthest_place(self):
        response = self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)})

        names = [p["name"] for p in response.data["places"]]
        self.assertNotIn("가장먼명소", names)

    def test_nearest_places_excludes_place_without_coordinates(self):
        response = self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)})

        names = [p["name"] for p in response.data["places"]]
        self.assertNotIn("좌표없는명소", names)

    def test_nearest_places_returns_exactly_three(self):
        response = self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)})

        self.assertEqual(len(response.data["places"]), 3)


class RecommendationViewRandomFallbackTest(RecommendTestData):
    """checklist 3, 4, 7: 위치 정보가 없거나/숫자가 아니거나/일부만 있으면 무작위 3곳으로 대체된다."""

    def setUp(self):
        super().setUp()
        for i in range(5):
            create_place_with_source(f"무작위명소{i}", "TEST_SOURCE", f"REC_RAND_{i}")

    def test_no_lat_lng_returns_three_places_without_error(self):
        response = self.client.get(RECOMMEND_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)

    def test_non_numeric_lat_lng_falls_back_to_random_without_error(self):
        response = self.client.get(RECOMMEND_URL, {"lat": "정보없음", "lng": "정보없음"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)

    def test_only_lat_without_lng_falls_back_to_random(self):
        response = self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)

    def test_only_lng_without_lat_falls_back_to_random(self):
        response = self.client.get(RECOMMEND_URL, {"lng": str(BASE_LNG)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)

    def test_empty_string_lat_lng_falls_back_to_random(self):
        response = self.client.get(RECOMMEND_URL, {"lat": "", "lng": ""})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)

    def test_response_place_fields_match_serializer(self):
        response = self.client.get(RECOMMEND_URL)

        place = response.data["places"][0]
        self.assertEqual(set(place.keys()), {"id", "name", "address", "photo_url"})


class RecommendationViewFewerThanThreeTest(RecommendTestData):
    """checklist 5: 명소가 3개보다 적어도 에러 없이 있는 만큼만 반환한다."""

    def test_random_branch_with_one_place_returns_one_without_error(self):
        create_place_with_source("유일한명소", "TEST_SOURCE", "REC_ONLY1")

        response = self.client.get(RECOMMEND_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 1)
        self.assertEqual(response.data["places"][0]["name"], "유일한명소")

    def test_nearest_branch_with_one_place_returns_one_without_error(self):
        create_place_with_source(
            "유일한명소", "TEST_SOURCE", "REC_ONLY2", latitude=Decimal("37.5665"), longitude=Decimal("126.9780")
        )

        response = self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 1)

    def test_no_places_at_all_returns_empty_list_without_error(self):
        response = self.client.get(RECOMMEND_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["places"], [])


# ---------------------------------------------------------------------------
# Phase 2-5 (명소 상세 + 카카오맵) checklist tests. See docs/PHASES/PHASE2.md 2-5.
# ---------------------------------------------------------------------------

DETAIL_URL_TEMPLATE = "/api/places/{}/"


def _fake_kakao_result(name, address, lat, lng, category="음식점", kakao_id="1"):
    return {
        "id": kakao_id,
        "place_name": name,
        "address_name": address,
        "road_address_name": address,
        "latitude": lat,
        "longitude": lng,
        "category_name": category,
    }


class PlaceDetailTestData(TestCase):
    """명소 상세 테스트에서 공통으로 쓰는 명소/작품 데이터를 만든다."""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}

        self.place = create_place_with_source(
            "경복궁",
            "TEST_SOURCE",
            "DETAIL_S1",
            address="서울 종로구 사직로 161",
            photo_url="https://example.com/gyeongbokgung.jpg",
            business_hours="09:00~18:00",
            recommended_time="5월, 초저녁",
            photo_tips="근정전 앞에서 대각선 구도",
            etiquette="나무를 꺾지 말아주세요",
            description="조선시대 정궁",
            latitude=Decimal("37.579617"),
            longitude=Decimal("126.977041"),
        )


class PlaceDetailViewLoginNotRequiredTest(PlaceDetailTestData):
    """checklist: 로그인 없이 열린다 / 무효 만료 토큰이어도 401이 아니라 200이 온다."""

    def test_detail_without_token_returns_200(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("accounts.authentication.verify_id_token")
    def test_detail_with_invalid_token_still_returns_200(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "경복궁")

    @patch("accounts.authentication.verify_id_token")
    def test_detail_with_expired_token_still_returns_200(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PlaceDetailViewBasicFieldsTest(PlaceDetailTestData):
    """checklist: 명소 기본 정보(이름 주소 사진 영업시간 설명 위경도)가 함께 나온다."""

    def test_detail_includes_basic_fields(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "경복궁")
        self.assertEqual(response.data["address"], "서울 종로구 사직로 161")
        self.assertEqual(response.data["photo_url"], "https://example.com/gyeongbokgung.jpg")
        self.assertEqual(response.data["business_hours"], "09:00~18:00")
        self.assertEqual(response.data["description"], "조선시대 정궁")
        self.assertAlmostEqual(float(response.data["latitude"]), 37.579617, places=5)
        self.assertAlmostEqual(float(response.data["longitude"]), 126.977041, places=5)

    def test_detail_includes_recommended_time_photo_tips_etiquette(self):
        """여운 API 명세서의 명소 상세 필드 (DETAIL_SPEC 6-1 #25)."""
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["recommended_time"], "5월, 초저녁")
        self.assertEqual(response.data["photo_tips"], "근정전 앞에서 대각선 구도")
        self.assertEqual(response.data["etiquette"], "나무를 꺾지 말아주세요")

    def test_new_admin_fields_default_to_empty_string(self):
        bare = create_place_with_source("빈명소", "TEST_SOURCE", "DETAIL_BARE")

        response = self.client.get(DETAIL_URL_TEMPLATE.format(bare.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["recommended_time"], "")
        self.assertEqual(response.data["photo_tips"], "")
        self.assertEqual(response.data["etiquette"], "")


class PlaceDetailViewWorksTest(PlaceDetailTestData):
    """checklist: 명소를 열면 등장 작품과 작품별 장면 설명이 같이 나온다."""

    def setUp(self):
        super().setUp()
        self.work1 = Work.objects.create(
            title="사랑비",
            category=Work.Category.DRAMA,
            release_date="2022-01-01",
            main_cast="배우A",
            director="감독A",
        )
        self.work2 = Work.objects.create(
            title="극한직업",
            category=Work.Category.MOVIE,
            release_date="2019-01-01",
            main_cast="배우B",
            director="감독B",
        )
        PlaceWork.objects.create(place=self.place, work=self.work1, scene_description="1화 왕궁 장면")
        PlaceWork.objects.create(place=self.place, work=self.work2, scene_description="추격 장면")

    def test_detail_includes_all_linked_works(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = {w["work"]["title"] for w in response.data["works"]}
        self.assertEqual(titles, {"사랑비", "극한직업"})

    def test_scene_description_matches_correct_work(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        by_title = {w["work"]["title"]: w["scene_description"] for w in response.data["works"]}
        self.assertEqual(by_title["사랑비"], "1화 왕궁 장면")
        self.assertEqual(by_title["극한직업"], "추격 장면")

    def test_work_detail_fields_are_included(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        work_entry = next(w for w in response.data["works"] if w["work"]["title"] == "사랑비")
        self.assertEqual(work_entry["work"]["category"], "DRAMA")
        self.assertEqual(work_entry["work"]["main_cast"], "배우A")
        self.assertEqual(work_entry["work"]["director"], "감독A")

    def test_place_without_works_returns_empty_list(self):
        lonely_place = create_place_with_source("혼자인명소", "TEST_SOURCE", "DETAIL_LONELY")

        response = self.client.get(DETAIL_URL_TEMPLATE.format(lonely_place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["works"], [])


class PlaceDetailViewNotFoundTest(PlaceDetailTestData):
    """checklist: 없는 명소를 열려고 하면 존재하지 않습니다가 나온다."""

    def test_missing_place_returns_404_with_message(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "존재하지 않습니다")


class PlaceDetailViewNearbyPlacesTest(PlaceDetailTestData):
    """checklist: 주변 상권이 보인다. 카카오 API는 mock으로 처리해 실제 네트워크 호출을 하지 않는다."""

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_nearby_places_are_included_from_mocked_kakao_api(self, mock_search):
        mock_search.side_effect = [
            [_fake_kakao_result("맛집1", "서울 종로구 1", 37.58, 126.98, "음식점", kakao_id="F1")],
            [_fake_kakao_result("카페1", "서울 종로구 2", 37.581, 126.981, "카페", kakao_id="C1")],
            [_fake_kakao_result("관광지1", "서울 종로구 3", 37.582, 126.982, "관광명소", kakao_id="A1")],
        ]

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {p["place_name"] for p in response.data["nearby_places"]}
        self.assertEqual(names, {"맛집1", "카페1", "관광지1"})
        self.assertEqual(mock_search.call_count, 3)

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_nearby_places_search_uses_place_coordinates_and_configured_radius(self, mock_search):
        mock_search.return_value = []

        self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        called_codes = [call.args[0] for call in mock_search.call_args_list]
        self.assertEqual(called_codes, ["FD6", "CE7", "AT4"])
        for call in mock_search.call_args_list:
            self.assertAlmostEqual(call.kwargs["x"], 126.977041, places=5)
            self.assertAlmostEqual(call.kwargs["y"], 37.579617, places=5)
            self.assertEqual(call.kwargs["radius"], 1000)

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_one_category_failing_does_not_break_response(self, mock_search):
        def side_effect(category_code, **kwargs):
            if category_code == "CE7":
                raise Exception("카카오 카페 검색 실패")
            if category_code == "FD6":
                return [_fake_kakao_result("맛집1", "서울 종로구 1", 37.58, 126.98, "음식점", kakao_id="F1")]
            return [_fake_kakao_result("관광지1", "서울 종로구 3", 37.582, 126.982, "관광명소", kakao_id="A1")]

        mock_search.side_effect = side_effect

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = {p["place_name"] for p in response.data["nearby_places"]}
        self.assertEqual(names, {"맛집1", "관광지1"})

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_all_categories_failing_returns_200_with_empty_nearby_places(self, mock_search):
        mock_search.side_effect = Exception("카카오 API 전체 실패")

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nearby_places"], [])

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_place_without_coordinates_skips_kakao_call_and_returns_empty_list(self, mock_search):
        no_coord_place = create_place_with_source("좌표없는명소", "TEST_SOURCE", "DETAIL_NOCOORD")

        response = self.client.get(DETAIL_URL_TEMPLATE.format(no_coord_place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nearby_places"], [])
        mock_search.assert_not_called()

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_duplicate_result_across_categories_is_deduplicated_by_kakao_id(self, mock_search):
        duplicate_place = _fake_kakao_result("복합공간", "서울 종로구 4", 37.583, 126.983, "복합", kakao_id="DUP1")
        mock_search.side_effect = [
            [duplicate_place],
            [duplicate_place],
            [],
        ]

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["nearby_places"]), 1)
        self.assertEqual(response.data["nearby_places"][0]["place_name"], "복합공간")

    @patch("places.views.kakao_geocoding.search_by_category")
    def test_nearby_places_are_capped_at_fifteen(self, mock_search):
        # 카테고리마다 서로 다른 id를 써야 한다. 같은 id를 쓰면 중복 제거만으로도
        # 15개 이하로 줄어들어서, 정작 자르는(cap) 코드가 없어도 테스트가 통과해버린다.
        food_results = [
            _fake_kakao_result(f"식당{i}", f"서울 종로구 {i}", 37.58, 126.98, "음식점", kakao_id=f"F{i}")
            for i in range(20)
        ]
        cafe_results = [
            _fake_kakao_result(f"카페{i}", f"서울 종로구 {i}", 37.58, 126.98, "카페", kakao_id=f"C{i}")
            for i in range(20)
        ]
        tourist_results = [
            _fake_kakao_result(f"명소{i}", f"서울 종로구 {i}", 37.58, 126.98, "관광명소", kakao_id=f"A{i}")
            for i in range(20)
        ]
        mock_search.side_effect = [food_results, cafe_results, tourist_results]

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 서로 겹치지 않는 60개(20+20+20) 중 15개로 정확히 잘려야 한다.
        self.assertEqual(len(response.data["nearby_places"]), 15)


# ---------------------------------------------------------------------------
# Phase 3 사이클 B (검색이력 기반 추천 고도화) checklist tests. See docs/PHASES/PHASE3.md 3번,
# places/views.py _personalized_places 참고.
#
# 확정된 알고리즘 (coding이 구현, 2026-08-19 정해짐): 로그인 + 위치 있음이면 가장 가까운
# 후보 10곳(RECOMMEND_CANDIDATE_POOL)을 뽑고, 각 후보에 가산점을 매긴다 - 검색이력
# 키워드가 명소 이름/등장 작품 제목에 포함되면 키워드당 +5점, 즐겨찾기 1건당 +1점,
# 감춰지지 않은 리뷰 1건당 +1점. 점수 내림차순, 동점이면 거리 가까운 순 -> id 작은 순으로
# 정렬해 상위 3곳을 돌려준다. 로그인이어도 위치가 없으면(또는 비로그인) Phase 2와 동일하게
# 거리순/무작위로 동작한다.
# ---------------------------------------------------------------------------

from favorites.models import Favorite
from reviews.models import Review


def create_member(uid, nickname="테스터"):
    return Member.objects.create(
        firebase_uid=uid,
        provider=Member.Provider.GOOGLE,
        nickname=nickname,
        agreed_terms_at="2026-01-01T00:00:00Z",
    )


class PersonalizedRecommendTestData(TestCase):
    """개인화 추천 테스트에서 공통으로 쓰는 로그인 회원 준비."""

    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.member = create_member("personal-uid-1")


class PersonalizedRecommendationKeywordTest(PersonalizedRecommendTestData):
    """checklist: 로그인 + 위치 있음 + 검색이력 있음 -> 검색이력과 연관된 명소가 우선 추천된다."""

    def setUp(self):
        super().setUp()
        self.near1 = create_place_with_source(
            "일반명소1", "TEST_SOURCE", "PERS_N1",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        self.near2 = create_place_with_source(
            "일반명소2", "TEST_SOURCE", "PERS_N2",
            latitude=Decimal("37.5700"), longitude=Decimal(str(BASE_LNG)),
        )
        self.near3 = create_place_with_source(
            "일반명소3", "TEST_SOURCE", "PERS_N3",
            latitude=Decimal("37.5750"), longitude=Decimal(str(BASE_LNG)),
        )
        self.near4 = create_place_with_source(
            "일반명소4", "TEST_SOURCE", "PERS_N4",
            latitude=Decimal("37.5800"), longitude=Decimal(str(BASE_LNG)),
        )
        self.far_matching = create_place_with_source(
            "특별한장소E5", "TEST_SOURCE", "PERS_FAR",
            latitude=Decimal("37.6000"), longitude=Decimal(str(BASE_LNG)),
        )
        SearchHistory.objects.create(member=self.member, keyword="특별한장소")

    @patch("accounts.authentication.verify_id_token")
    def test_keyword_matched_place_is_ranked_first_despite_being_farthest(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names[0], "특별한장소E5")
        self.assertEqual(names[1:], ["일반명소1", "일반명소2"])


class PersonalizedRecommendationWorkTitleMatchTest(PersonalizedRecommendTestData):
    """checklist: 검색이력 키워드가 명소 이름이 아니라 연결된 작품 제목에 있어도 가산점을 받는다."""

    def setUp(self):
        super().setUp()
        self.work_matched_place = create_place_with_source(
            "이름은평범한명소", "TEST_SOURCE", "PERS_WORK_MATCH",
            latitude=Decimal("37.6500"), longitude=Decimal(str(BASE_LNG)),
        )
        matched_work = Work.objects.create(title="사랑비특별판", category=Work.Category.DRAMA)
        PlaceWork.objects.create(place=self.work_matched_place, work=matched_work, scene_description="장면")

        self.unmatched_close_place = create_place_with_source(
            "가까운무관계명소", "TEST_SOURCE", "PERS_WORK_UNMATCHED",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        SearchHistory.objects.create(member=self.member, keyword="사랑비특별판")

    @patch("accounts.authentication.verify_id_token")
    def test_place_ranked_up_by_matching_linked_work_title(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names[0], "이름은평범한명소")


class PersonalizedRecommendationPopularityTest(PersonalizedRecommendTestData):
    """checklist: 즐겨찾기/리뷰 개수 차이가 있으면 많은 쪽이 우선 추천된다."""

    def setUp(self):
        super().setUp()
        self.close_no_popularity = create_place_with_source(
            "인기없는가까운명소", "TEST_SOURCE", "PERS_POP_LOW",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        self.far_popular = create_place_with_source(
            "인기많은먼명소", "TEST_SOURCE", "PERS_POP_HIGH",
            latitude=Decimal("37.6500"), longitude=Decimal(str(BASE_LNG)),
        )
        for i in range(3):
            fav_member = create_member(f"fav-uid-{i}")
            Favorite.objects.create(member=fav_member, place=self.far_popular)
        for i in range(2):
            review_member = create_member(f"review-uid-{i}")
            Review.objects.create(
                member=review_member, place=self.far_popular, rating=5, content="좋아요", language="ko"
            )

    @patch("accounts.authentication.verify_id_token")
    def test_place_with_more_favorites_and_reviews_is_ranked_first(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names[0], "인기많은먼명소")

    @patch("accounts.authentication.verify_id_token")
    def test_hidden_reviews_do_not_count_toward_score(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")
        for i in range(5):
            hidden_member = create_member(f"hidden-review-uid-{i}")
            Review.objects.create(
                member=hidden_member,
                place=self.close_no_popularity,
                rating=1,
                content="스팸",
                language="ko",
                is_hidden=True,
            )

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names[0], "인기많은먼명소")


class PersonalizedRecommendationNewMemberTest(PersonalizedRecommendTestData):
    """checklist: 검색이력/즐겨찾기/리뷰가 전혀 없는 새 회원은 거리순 추천과 동일하다."""

    def setUp(self):
        super().setUp()
        self.near = create_place_with_source(
            "가까운명소", "TEST_SOURCE", "PERS_NEW_NEAR",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        self.mid = create_place_with_source(
            "중간명소", "TEST_SOURCE", "PERS_NEW_MID",
            latitude=Decimal("37.6000"), longitude=Decimal(str(BASE_LNG)),
        )
        self.far = create_place_with_source(
            "먼명소", "TEST_SOURCE", "PERS_NEW_FAR",
            latitude=Decimal("37.7000"), longitude=Decimal(str(BASE_LNG)),
        )

    @patch("accounts.authentication.verify_id_token")
    def test_new_member_without_history_gets_distance_order(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names, ["가까운명소", "중간명소", "먼명소"])


class PersonalizedRecommendationTieBreakTest(PersonalizedRecommendTestData):
    """checklist: 동점(가산점도 거리도 같음)이면 id가 작은 순으로 결정론적으로 정렬된다."""

    def setUp(self):
        super().setUp()
        self.tie_low_id = create_place_with_source(
            "동점명소A", "TEST_SOURCE", "PERS_TIE_A",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        self.tie_high_id = create_place_with_source(
            "동점명소B", "TEST_SOURCE", "PERS_TIE_B",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        self.third = create_place_with_source(
            "세번째명소", "TEST_SOURCE", "PERS_TIE_C",
            latitude=Decimal("37.6500"), longitude=Decimal(str(BASE_LNG)),
        )
        self.assertLess(self.tie_low_id.id, self.tie_high_id.id)

    @patch("accounts.authentication.verify_id_token")
    def test_tie_break_order_is_by_id_and_deterministic_across_calls(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response1 = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )
        response2 = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        expected = ["동점명소A", "동점명소B", "세번째명소"]
        self.assertEqual([p["name"] for p in response1.data["places"]], expected)
        self.assertEqual([p["name"] for p in response2.data["places"]], expected)


class PersonalizedRecommendationNoLocationTest(PersonalizedRecommendTestData):
    """checklist: 위치 없이 로그인만 한 경우 개인화가 적용되지 않고 Phase 2 방식(무작위)이 유지된다."""

    def setUp(self):
        super().setUp()
        for i in range(5):
            create_place_with_source(f"무작위대상{i}", "TEST_SOURCE", f"PERS_RAND_{i}")

    @patch("places.views._personalized_places")
    @patch("accounts.authentication.verify_id_token")
    def test_personalized_places_is_not_called_without_location(self, mock_verify, mock_personalized):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(RECOMMEND_URL, **self.auth_header)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)
        mock_personalized.assert_not_called()

    @patch("places.views._personalized_places")
    @patch("accounts.authentication.verify_id_token")
    def test_personalized_places_is_called_when_logged_in_with_location(self, mock_verify, mock_personalized):
        mock_verify.return_value = make_decoded_token("personal-uid-1")
        mock_personalized.return_value = []

        self.client.get(RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header)

        mock_personalized.assert_called_once()


class PersonalizedRecommendationInvalidTokenTest(PersonalizedRecommendTestData):
    """checklist: 위치가 있는 분기에서도 무효 토큰으로 호출하면 401이 아니라 200이 온다."""

    def setUp(self):
        super().setUp()
        create_place_with_source(
            "명소", "TEST_SOURCE", "PERS_INVALID_TOKEN",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_with_location_returns_200_not_401(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PersonalizedRecommendationFewerThanPoolTest(PersonalizedRecommendTestData):
    """checklist: 전체 명소가 후보 풀(10곳)보다 적어도 에러 없이 동작한다."""

    def setUp(self):
        super().setUp()
        for i in range(5):
            create_place_with_source(
                f"소규모명소{i}", "TEST_SOURCE", f"PERS_FEW_{i}",
                latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
            )

    @patch("accounts.authentication.verify_id_token")
    def test_personalized_branch_with_fewer_places_than_pool_size_does_not_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 3)


class PersonalizedRecommendationKeywordAccumulationTest(PersonalizedRecommendTestData):
    """checklist: 같은 명소가 검색이력 키워드 여러 개와 매칭되면 가산점이 매칭 개수만큼 정확히 쌓인다.

    키워드 2개가 모두 매칭되는 명소(10점)가, 즐겨찾기 9건(9점)에 더 가까운 다른 명소보다
    앞서야 한다. 키워드 매칭 개수를 누적하지 않고 있는지 없는지로만 보는 버그가 있다면
    5점 < 9점이 되어 이 테스트가 실패하며 버그를 잡아낸다.
    """

    def setUp(self):
        super().setUp()
        self.multi_match = create_place_with_source(
            "제주감귤촬영지백", "TEST_SOURCE", "PERS_MULTI",
            latitude=Decimal("37.6500"), longitude=Decimal(str(BASE_LNG)),
        )
        self.many_favorites = create_place_with_source(
            "즐겨찾기아홉개장소", "TEST_SOURCE", "PERS_FAVS9",
            latitude=Decimal(str(BASE_LAT)), longitude=Decimal(str(BASE_LNG)),
        )
        for i in range(9):
            fav_member = create_member(f"multi-fav-uid-{i}")
            Favorite.objects.create(member=fav_member, place=self.many_favorites)

        SearchHistory.objects.create(member=self.member, keyword="제주감귤")
        SearchHistory.objects.create(member=self.member, keyword="촬영지백")

    @patch("accounts.authentication.verify_id_token")
    def test_multiple_keyword_matches_accumulate_score_and_outrank_higher_favorite_count(self, mock_verify):
        mock_verify.return_value = make_decoded_token("personal-uid-1")

        response = self.client.get(
            RECOMMEND_URL, {"lat": str(BASE_LAT), "lng": str(BASE_LNG)}, **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names[0], "제주감귤촬영지백")


# ---------------------------------------------------------------------------
# Phase 4 (다국어 번역 — 명소·작품만) checklist tests. See docs/PHASES/PHASE4.md 4-3.
# ---------------------------------------------------------------------------

import requests as requests_module
from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.cookie import CookieStorage
from django.test import RequestFactory, override_settings

from places.admin import PlaceTranslationAdmin, WorkTranslationAdmin, retranslate_places, retranslate_works
from places.models import TranslationStatus
from places.sources import google_translate
from places.translation import pick_translated_text, translate_place, translate_work


class GoogleTranslateModuleTest(TestCase):
    """저수준 API 호출 모듈. requests를 mock해서 실제 네트워크를 타지 않는다."""

    @patch("places.sources.google_translate.requests.post")
    def test_translate_text_returns_translated_string(self, mock_post):
        mock_post.return_value.json.return_value = {
            "data": {"translations": [{"translatedText": "Gyeongbokgung"}]}
        }
        mock_post.return_value.raise_for_status.return_value = None

        with override_settings(GOOGLE_TRANSLATE_API_KEY="fake-key"):
            result = google_translate.translate_text("경복궁", "en")

        self.assertEqual(result, "Gyeongbokgung")

    def test_translate_text_without_api_key_raises(self):
        with override_settings(GOOGLE_TRANSLATE_API_KEY=""):
            with self.assertRaises(RuntimeError):
                google_translate.translate_text("경복궁", "en")

    @patch("places.sources.google_translate.requests.post")
    def test_translate_text_propagates_http_error(self, mock_post):
        mock_post.return_value.raise_for_status.side_effect = requests_module.HTTPError("500")

        with override_settings(GOOGLE_TRANSLATE_API_KEY="fake-key"):
            with self.assertRaises(requests_module.HTTPError):
                google_translate.translate_text("경복궁", "en")


class TranslatePlaceServiceTest(TestCase):
    """checklist: 실패 판정 규칙(빈 값/원문과 동일/길이/시간초과·오류), 짧은 이름은 길이 검사를 건너뛴다."""

    @patch("places.translation.google_translate.translate_text")
    def test_success_sets_status_success_and_fields(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR1", description="조선시대 정궁")
        mock_translate.side_effect = ["Gyeongbokgung", "Royal palace of the Joseon dynasty"]

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(translation.name, "Gyeongbokgung")
        self.assertEqual(translation.description, "Royal palace of the Joseon dynasty")
        self.assertIsNotNone(translation.translated_at)
        self.assertFalse(translation.is_approved)

    @patch("places.translation.google_translate.translate_text")
    def test_blank_description_is_not_translated_and_does_not_fail(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR2")
        mock_translate.return_value = "Gyeongbokgung"

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(translation.description, "")
        self.assertEqual(mock_translate.call_count, 1)  # description은 빈 값이라 아예 호출 안 됨

    @patch("places.translation.google_translate.translate_text")
    def test_exception_from_api_marks_failed(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR3")
        mock_translate.side_effect = TimeoutError("시간 초과")

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)
        self.assertIsNone(translation.translated_at)

    @patch("places.translation.google_translate.translate_text")
    def test_empty_result_marks_failed(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR4")
        mock_translate.return_value = ""

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)

    @patch("places.translation.google_translate.translate_text")
    def test_result_same_as_original_marks_failed(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR5")
        mock_translate.return_value = "경복궁"  # 번역이 안 되고 그대로 돌아옴

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)

    @patch("places.translation.google_translate.translate_text")
    def test_long_description_with_bad_length_ratio_marks_failed(self, mock_translate):
        # 원문이 20자를 넘으므로 길이 검사가 적용된다. 번역문이 원문의 1/5보다 훨씬 짧다.
        description = "이 설명은 스무 글자를 확실히 넘기기 위한 아주 긴 문장입니다"  # 20자 초과
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR6", description=description)
        mock_translate.side_effect = ["Gyeongbokgung", "Hi"]  # 이름은 성공, 설명은 너무 짧음

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)
        # 성공한 필드(name)는 그대로 반영된다.
        self.assertEqual(translation.name, "Gyeongbokgung")

    @patch("places.translation.google_translate.translate_text")
    def test_short_name_skips_length_check(self, mock_translate):
        """checklist: 짧은 명소 이름이 길이 검사 때문에 실패로 처리되지 않는다.

        `청계천`(3자) → `Cheonggyecheon`(14자)은 4.7배라 5배 기준에 걸릴 뻔하지만,
        원문이 20자 이하이므로 애초에 길이 검사를 받지 않아야 한다 (DETAIL_SPEC 4-3).
        """
        place = create_place_with_source("청계천", "TEST_SOURCE", "TR7")
        mock_translate.return_value = "Cheonggyecheon"

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(translation.name, "Cheonggyecheon")

    @patch("places.translation.google_translate.translate_text")
    def test_partial_failure_keeps_previous_successful_field_value(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR8", description="조선시대 정궁")
        PlaceTranslation.objects.create(
            place=place,
            language="en",
            name="OldName",
            description="Old description",
            status=TranslationStatus.SUCCESS,
            is_approved=True,
        )
        mock_translate.side_effect = ["Gyeongbokgung", "조선시대 정궁"]  # 이름은 성공, 설명은 원문 그대로(실패)

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)
        self.assertEqual(translation.name, "Gyeongbokgung")  # 성공한 값으로 갱신됨
        self.assertEqual(translation.description, "Old description")  # 실패한 필드는 이전 값 유지
        # 내용이 바뀌었으니 재승인이 필요하다 — 예전에 승인됐어도 초기화한다.
        self.assertFalse(translation.is_approved)

    @patch("places.translation.google_translate.translate_text")
    def test_complete_failure_keeps_existing_approval(self, mock_translate):
        """회귀 테스트: 이미 승인되어 노출 중인 번역이, 재번역이 완전히 실패했을 때도 그대로 유지돼야 한다.

        내용이 하나도 안 바뀌었는데 is_approved가 False로 리셋되면, 정상 노출 중이던 번역이
        일시적인 API 실패 한 번 때문에 사용자 화면에서 사라져 버린다 (버그 리포트 재현 시나리오).
        """
        place = create_place_with_source("경복궁", "TEST_SOURCE", "TR9", description="조선시대 정궁")
        PlaceTranslation.objects.create(
            place=place,
            language="en",
            name="Gyeongbokgung",
            description="Royal palace of the Joseon dynasty",
            status=TranslationStatus.SUCCESS,
            is_approved=True,
        )
        mock_translate.side_effect = Exception("네트워크 타임아웃")  # 완전 실패

        translation = translate_place(place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)
        # 내용은 전혀 안 바뀌었다.
        self.assertEqual(translation.name, "Gyeongbokgung")
        self.assertEqual(translation.description, "Royal palace of the Joseon dynasty")
        # 그러니 기존 승인 상태도 그대로 유지돼야 한다.
        self.assertTrue(translation.is_approved)


class TranslationLengthRatioBoundaryTest(TestCase):
    """DETAIL_SPEC 4-3: 길이 비율 1/5~5배 경계값을 정확히 확인한다.
    원문이 20자를 넘을 때만 검사가 적용되므로, 25자 원문을 기준으로 잡는다.
    """

    def setUp(self):
        # 정확히 25자인 한국어 문자열 (설명 필드에 씀)
        self.long_description = "가" * 25
        self.place = create_place_with_source("테스트명소", "TEST_SOURCE", "LEN_BOUND")

    @patch("places.translation.google_translate.translate_text")
    def test_ratio_exactly_one_fifth_is_success(self, mock_translate):
        # 25자 / 5 = 5자 => ratio = 0.2 = 1/5 (경계값, 실패 아님)
        mock_translate.side_effect = ["ok-name", "a" * 5]
        self.place.description = self.long_description
        self.place.save()

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)

    @patch("places.translation.google_translate.translate_text")
    def test_ratio_just_below_one_fifth_fails(self, mock_translate):
        # 25자 / 4 = 4자 => ratio = 0.16 < 1/5 (실패)
        mock_translate.side_effect = ["ok-name", "a" * 4]
        self.place.description = self.long_description
        self.place.save()

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)

    @patch("places.translation.google_translate.translate_text")
    def test_ratio_exactly_five_is_success(self, mock_translate):
        # 25자 * 5 = 125자 => ratio = 5.0 (경계값, 실패 아님)
        mock_translate.side_effect = ["ok-name", "a" * 125]
        self.place.description = self.long_description
        self.place.save()

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)

    @patch("places.translation.google_translate.translate_text")
    def test_ratio_just_above_five_fails(self, mock_translate):
        # 25자 * 5 + 1 = 126자 => ratio = 5.04 > 5 (실패)
        mock_translate.side_effect = ["ok-name", "a" * 126]
        self.place.description = self.long_description
        self.place.save()

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)

    @patch("places.translation.google_translate.translate_text")
    def test_source_length_exactly_20_skips_length_check(self, mock_translate):
        # 정확히 20자인 원문은 길이검사 대상이 아니어야 한다 ("20자가 넘는 글에만 적용")
        description_20 = "가" * 20
        mock_translate.side_effect = ["ok-name", "a"]  # 극단적으로 짧은 번역
        self.place.description = description_20
        self.place.save()

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)

    @patch("places.translation.google_translate.translate_text")
    def test_source_length_21_applies_length_check(self, mock_translate):
        # 21자부터는 길이검사가 걸려야 한다
        description_21 = "가" * 21
        mock_translate.side_effect = ["ok-name", "a"]  # 극단적으로 짧은 번역 -> 실패해야 함
        self.place.description = description_21
        self.place.save()

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)


class TranslationMaxLengthTest(TestCase):
    """PlaceTranslation.name은 CharField(max_length=200). 번역 결과가 200자를 넘으면 잘라서 저장하는지 확인한다.

    (버그 수정 확인용) name/title에 해당하는 필드를 저장 전에 자르지 않으면 Postgres가
    DataError를 던져서 명소 등록 시 자동 번역(on_commit)이나 admin "다시 번역" 액션이 죽는다.
    """

    def setUp(self):
        self.place = create_place_with_source("경복궁", "TEST_SOURCE", "MAXLEN1")

    @patch("places.translation.google_translate.translate_text")
    def test_translated_name_over_200_chars_is_truncated_and_saved(self, mock_translate):
        # 원문(경복궁, 3자)은 20자 이하라 길이검사를 안 받으므로, 번역기가 극단적으로 긴 결과를
        # 줘도(예: 250자) 길이 비율만으로는 실패 처리되지 않는다. 잘려서 저장돼야 한다.
        long_name = "a" * 250
        mock_translate.side_effect = [long_name, ""]

        translation = translate_place(self.place, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(len(translation.name), 200)
        self.assertEqual(translation.name, long_name[:200])


class TranslateWorkServiceTest(TestCase):
    """TranslatePlaceServiceTest와 같은 규칙이 작품(Work)에도 적용되는지 확인."""

    @patch("places.translation.google_translate.translate_text")
    def test_success_sets_status_success_and_fields(self, mock_translate):
        work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA, description="로맨스 드라마")
        mock_translate.side_effect = ["Rain of Love", "A romance drama"]

        translation = translate_work(work, "en")

        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(translation.title, "Rain of Love")
        self.assertEqual(translation.description, "A romance drama")
        self.assertFalse(translation.is_approved)

    @patch("places.translation.google_translate.translate_text")
    def test_exception_marks_failed_but_row_is_kept(self, mock_translate):
        work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA)
        mock_translate.side_effect = Exception("번역 서비스 오류")

        translation = translate_work(work, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)
        self.assertTrue(WorkTranslation.objects.filter(pk=translation.pk).exists())

    @patch("places.translation.google_translate.translate_text")
    def test_complete_failure_keeps_existing_approval(self, mock_translate):
        """회귀 테스트(Work판): 완전 실패 시 내용이 안 바뀌었으면 기존 승인 상태를 유지한다."""
        work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA, description="로맨스 드라마")
        WorkTranslation.objects.create(
            work=work,
            language="en",
            title="Rain of Love",
            description="A romance drama",
            status=TranslationStatus.SUCCESS,
            is_approved=True,
        )
        mock_translate.side_effect = Exception("번역 서비스 오류")

        translation = translate_work(work, "en")

        self.assertEqual(translation.status, TranslationStatus.FAILED)
        self.assertEqual(translation.title, "Rain of Love")
        self.assertEqual(translation.description, "A romance drama")
        self.assertTrue(translation.is_approved)


class PickTranslatedTextTest(TestCase):
    """checklist: 승인 전에는 번역문이 안 보이고, 승인하면 보인다 / 번역이 없으면 원문이 나온다."""

    def setUp(self):
        self.place = create_place_with_source("경복궁", "TEST_SOURCE", "PICK1", description="조선시대 정궁")

    def test_no_translation_returns_original(self):
        self.assertEqual(pick_translated_text(self.place, "name", "en"), "경복궁")

    def test_language_none_returns_original_even_if_translation_exists(self):
        PlaceTranslation.objects.create(
            place=self.place, language="en", name="Gyeongbokgung", is_approved=True
        )
        self.assertEqual(pick_translated_text(self.place, "name", None), "경복궁")

    def test_unapproved_translation_returns_original(self):
        PlaceTranslation.objects.create(
            place=self.place, language="en", name="Gyeongbokgung", is_approved=False
        )
        self.assertEqual(pick_translated_text(self.place, "name", "en"), "경복궁")

    def test_approved_translation_returns_translated_value(self):
        PlaceTranslation.objects.create(
            place=self.place, language="en", name="Gyeongbokgung", is_approved=True
        )
        self.assertEqual(pick_translated_text(self.place, "name", "en"), "Gyeongbokgung")


class PlaceTranslationSignalTest(TestCase):
    """checklist: 관리자가 명소·작품을 등록하면(신규 생성) 번역문이 자동으로 만들어진다.

    google_translate.translate_text를 mock해서 실제 네트워크를 타지 않는다. 번역은
    transaction.on_commit으로 미뤄지므로, TestCase의 captureOnCommitCallbacks로 직접 실행해줘야 한다.
    """

    @patch("places.translation.google_translate.translate_text")
    def test_creating_place_triggers_translation(self, mock_translate):
        mock_translate.return_value = "Gyeongbokgung"

        with self.captureOnCommitCallbacks(execute=True):
            place = Place.objects.create(name="경복궁")

        translation = PlaceTranslation.objects.get(place=place, language="en")
        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(translation.name, "Gyeongbokgung")
        self.assertFalse(translation.is_approved)

    @patch("places.translation.google_translate.translate_text")
    def test_updating_place_does_not_retranslate_automatically(self, mock_translate):
        """등록 시점에만 자동 번역하고, 그 뒤 내용 수정은 관리자가 admin의 "다시 번역"으로 직접 걸어야 한다."""
        mock_translate.return_value = "Gyeongbokgung"

        with self.captureOnCommitCallbacks(execute=True):
            place = Place.objects.create(name="경복궁")
        self.assertEqual(mock_translate.call_count, 1)

        with self.captureOnCommitCallbacks(execute=True):
            place.business_hours = "09:00~18:00"
            place.save()

        self.assertEqual(mock_translate.call_count, 1)

    @patch("places.translation.google_translate.translate_text")
    def test_creating_work_triggers_translation(self, mock_translate):
        mock_translate.return_value = "Rain of Love"

        with self.captureOnCommitCallbacks(execute=True):
            work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA)

        translation = WorkTranslation.objects.get(work=work, language="en")
        self.assertEqual(translation.status, TranslationStatus.SUCCESS)
        self.assertEqual(translation.title, "Rain of Love")


class TranslationAdminConfigTest(TestCase):
    """checklist: 실패한 명소가 관리자 화면의 실패 목록에 남는다 (status로 필터링 가능해야 한다)."""

    def test_place_translation_admin_exposes_status_filter_and_approval_editing(self):
        self.assertIn("status", PlaceTranslationAdmin.list_filter)
        self.assertIn("is_approved", PlaceTranslationAdmin.list_editable)

    def test_work_translation_admin_exposes_status_filter_and_approval_editing(self):
        self.assertIn("status", WorkTranslationAdmin.list_filter)
        self.assertIn("is_approved", WorkTranslationAdmin.list_editable)

    def test_failed_translation_can_be_found_by_status_filter(self):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "ADMIN_FAIL1")
        PlaceTranslation.objects.create(place=place, language="en", status=TranslationStatus.FAILED)

        failed = PlaceTranslation.objects.filter(status=TranslationStatus.FAILED)
        self.assertEqual(failed.count(), 1)


class TranslationAdminRetranslateActionTest(TestCase):
    """관리자가 "다시 번역" 액션을 실행하면 실제 번역 서비스가 호출되는지 확인."""

    def setUp(self):
        self.place_admin = PlaceTranslationAdmin(PlaceTranslation, AdminSite())
        self.work_admin = WorkTranslationAdmin(WorkTranslation, AdminSite())

    def _make_request(self):
        # message_user()가 쓸 메시지 저장소가 필요하다. CookieStorage는 세션 미들웨어 없이도 동작한다.
        request = RequestFactory().get("/admin/places/placetranslation/")
        request._messages = CookieStorage(request)
        return request

    @patch("places.admin.translate_place")
    def test_retranslate_places_action_calls_translate_place(self, mock_translate):
        place = create_place_with_source("경복궁", "TEST_SOURCE", "ADMIN_ACT1")
        translation = PlaceTranslation.objects.create(
            place=place, language="en", status=TranslationStatus.FAILED
        )

        retranslate_places(
            self.place_admin, self._make_request(), PlaceTranslation.objects.filter(pk=translation.pk)
        )

        mock_translate.assert_called_once_with(place, "en")

    @patch("places.admin.translate_work")
    def test_retranslate_works_action_calls_translate_work(self, mock_translate):
        work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA)
        translation = WorkTranslation.objects.create(
            work=work, language="en", status=TranslationStatus.FAILED
        )

        retranslate_works(
            self.work_admin, self._make_request(), WorkTranslation.objects.filter(pk=translation.pk)
        )

        mock_translate.assert_called_once_with(work, "en")


class TranslationApiIntegrationTest(TestCase):
    """checklist: 승인 전/후 노출, 언어 결정 순서(lang → 로그인 회원 언어 → 한국어),
    번역 실패해도 화면이 안 깨짐, 영어로 검색하면 한국어 명소가 찾아짐.
    """

    def setUp(self):
        self.client = APIClient()
        self.place = create_place_with_source(
            "경복궁", "TEST_SOURCE", "TRANS_INTEG_1", address="서울 종로구", description="조선시대 정궁"
        )
        self.translation = PlaceTranslation.objects.create(
            place=self.place,
            language="en",
            name="Gyeongbokgung",
            description="Royal palace of the Joseon dynasty",
            status=TranslationStatus.SUCCESS,
        )

    def test_unapproved_translation_not_shown_even_with_lang_param(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), {"lang": "en"})
        self.assertEqual(response.data["name"], "경복궁")

    def test_approved_translation_shown_with_lang_param(self):
        self.translation.is_approved = True
        self.translation.save()

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), {"lang": "en"})

        self.assertEqual(response.data["name"], "Gyeongbokgung")
        self.assertEqual(response.data["description"], "Royal palace of the Joseon dynasty")

    def test_non_translatable_fields_stay_korean(self):
        self.translation.is_approved = True
        self.translation.save()

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), {"lang": "en"})

        self.assertEqual(response.data["address"], "서울 종로구")

    def test_failed_translation_falls_back_to_korean_without_breaking_response(self):
        self.translation.status = TranslationStatus.FAILED
        self.translation.is_approved = False
        self.translation.save()

        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), {"lang": "en"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "경복궁")

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_language_used_without_lang_param(self, mock_verify):
        self.translation.is_approved = True
        self.translation.save()
        Member.objects.create(
            firebase_uid="lang-uid-1",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
            language="en",
        )
        mock_verify.return_value = make_decoded_token("lang-uid-1")

        response = self.client.get(
            DETAIL_URL_TEMPLATE.format(self.place.id), **{"HTTP_AUTHORIZATION": "Bearer fake-token"}
        )

        self.assertEqual(response.data["name"], "Gyeongbokgung")

    @patch("accounts.authentication.verify_id_token")
    def test_lang_param_overrides_member_language(self, mock_verify):
        """member.language가 en이 아니어도, lang 파라미터가 있으면 그게 우선한다."""
        self.translation.is_approved = True
        self.translation.save()
        Member.objects.create(
            firebase_uid="lang-uid-2",
            provider=Member.Provider.GOOGLE,
            agreed_terms_at="2026-01-01T00:00:00Z",
            language="ja",  # 지원하지 않는 언어라 매칭 안 됨 → lang 파라미터가 우선해야만 영어가 나옴
        )
        mock_verify.return_value = make_decoded_token("lang-uid-2")

        response = self.client.get(
            DETAIL_URL_TEMPLATE.format(self.place.id),
            {"lang": "en"},
            **{"HTTP_AUTHORIZATION": "Bearer fake-token"},
        )

        self.assertEqual(response.data["name"], "Gyeongbokgung")

    def test_search_result_name_shown_in_english_when_approved_and_lang_requested(self):
        self.translation.is_approved = True
        self.translation.save()

        response = self.client.get(SEARCH_URL, {"q": "경복궁", "lang": "en"})

        names = {p["name"] for p in response.data["places"]}
        self.assertIn("Gyeongbokgung", names)

    def test_english_keyword_search_finds_korean_place(self):
        """checklist: 영어로 Gyeongbokgung을 검색하면 경복궁이 찾아진다."""
        response = self.client.get(SEARCH_URL, {"q": "Gyeongbokgung"})

        names = {p["name"] for p in response.data["places"]}  # lang을 안 줬으니 기본은 한국어로 나온다
        self.assertIn("경복궁", names)


class WorkTranslationInPlaceDetailTest(TestCase):
    """checklist: 명소 상세에 중첩된 작품 정보(WorkDetailSerializer)도 번역된 값을 보여준다."""

    def setUp(self):
        self.client = APIClient()
        self.place = create_place_with_source("경복궁", "TEST_SOURCE", "WORK_TRANS_1")
        self.work = Work.objects.create(title="사랑비", category=Work.Category.DRAMA, description="로맨스 드라마")
        PlaceWork.objects.create(place=self.place, work=self.work, scene_description="1화 장면")
        WorkTranslation.objects.create(
            work=self.work,
            language="en",
            title="Rain of Love",
            description="A romance drama",
            status=TranslationStatus.SUCCESS,
            is_approved=True,
        )

    def test_nested_work_title_and_description_are_translated(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id), {"lang": "en"})

        work_entry = response.data["works"][0]["work"]
        self.assertEqual(work_entry["title"], "Rain of Love")
        self.assertEqual(work_entry["description"], "A romance drama")

    def test_nested_work_stays_korean_without_lang(self):
        response = self.client.get(DETAIL_URL_TEMPLATE.format(self.place.id))

        work_entry = response.data["works"][0]["work"]
        self.assertEqual(work_entry["title"], "사랑비")
