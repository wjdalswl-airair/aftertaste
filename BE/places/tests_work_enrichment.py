"""feature/be/work-drama: TMDB로 작품(Work) 줄거리·감독·방영일자·포스터 보강.

- 제목이 정확히 일치하는 TMDB 작품만 인정하는지 (pick_tmdb_match)
- 비어 있는 값만 채우고 관리자 값은 지키는지 (enrich_work)
- 못 찾은 작품은 손대지 않는지
- 커맨드가 건별 오류를 삼키고 끝까지 도는지
"""

import datetime
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from places.models import Work
from places.work_enrichment import enrich_work, normalize_title_for_match, pick_tmdb_match


def _candidate(tmdb_id, title, *, original_title=None, lang="ko", year=2016, popularity=10.0):
    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "original_title": original_title if original_title is not None else title,
        "original_language": lang,
        "release_year": year,
        "popularity": popularity,
    }


def _detail(tmdb_id, *, overview="줄거리입니다", director="김감독", release_date="2016-12-02", poster_path="/abc.jpg"):
    return {
        "tmdb_id": tmdb_id,
        "overview": overview,
        "director": director,
        "release_date": release_date,
        "poster_path": poster_path,
    }


class NormalizeTitleTest(TestCase):
    def test_strips_spaces_parens_and_casefolds(self):
        self.assertEqual(
            normalize_title_for_match("(아는 건 별로 없지만) 가족입니다"),
            normalize_title_for_match("아는 건 별로 없지만 가족입니다"),
        )
        self.assertEqual(normalize_title_for_match("Parasite"), normalize_title_for_match("parasite"))

    def test_empty_stays_empty(self):
        self.assertEqual(normalize_title_for_match(""), "")
        self.assertEqual(normalize_title_for_match(None), "")


class PickTmdbMatchTest(TestCase):
    def test_exact_title_match_is_picked(self):
        candidates = [_candidate(1, "도깨비")]
        match = pick_tmdb_match("도깨비", None, candidates)
        self.assertEqual(match["tmdb_id"], 1)

    def test_partial_or_noisy_title_is_not_accepted(self):
        # "기생충"으로 검색했을 때 섞여 나오는 다른 작품들
        candidates = [
            _candidate(2, "기생충을 예방하자", year=1990),
            _candidate(3, "흑인 도깨비 방망이", year=2000),
        ]
        self.assertIsNone(pick_tmdb_match("기생충", None, candidates))

    def test_matches_on_original_title(self):
        candidates = [_candidate(4, "Goblin", original_title="도깨비")]
        match = pick_tmdb_match("도깨비", None, candidates)
        self.assertEqual(match["tmdb_id"], 4)

    def test_year_far_off_is_rejected_when_work_has_release_date(self):
        candidates = [_candidate(5, "도깨비", year=1985)]
        self.assertIsNone(pick_tmdb_match("도깨비", datetime.date(2016, 12, 2), candidates))

    def test_year_within_tolerance_is_accepted(self):
        candidates = [_candidate(6, "도깨비", year=2017)]
        match = pick_tmdb_match("도깨비", datetime.date(2016, 12, 2), candidates)
        self.assertEqual(match["tmdb_id"], 6)

    def test_non_korean_original_is_dropped_then_picked_by_popularity(self):
        candidates = [
            _candidate(7, "도깨비", lang="en", popularity=99.0),  # 원어가 영어 → 제외
            _candidate(8, "도깨비", lang="ko", popularity=5.0),
            _candidate(9, "도깨비", lang="ko", popularity=50.0),
        ]
        match = pick_tmdb_match("도깨비", None, candidates)
        self.assertEqual(match["tmdb_id"], 9)

    def test_foreign_film_with_matching_korean_title_is_rejected_by_default(self):
        # "사랑에 관한 짧은 필름" == 폴란드 영화 Krótki film o miłości 의 한국어 제목
        candidates = [_candidate(31056, "사랑에 관한 짧은 필름", original_title="Krótki film o miłości", lang="pl")]
        self.assertIsNone(pick_tmdb_match("사랑에 관한 짧은 필름", None, candidates))

    def test_allow_foreign_accepts_non_korean_original(self):
        candidates = [_candidate(31056, "사랑에 관한 짧은 필름", original_title="Krótki film o miłości", lang="pl")]
        match = pick_tmdb_match("사랑에 관한 짧은 필름", None, candidates, require_korean=False)
        self.assertEqual(match["tmdb_id"], 31056)


@override_settings(
    TMDB_API_KEY="test-token",
    TMDB_IMAGE_BASE_URL="https://image.tmdb.org/t/p",
    TMDB_POSTER_SIZE="w500",
)
class EnrichWorkTest(TestCase):
    def _mock(self, candidates, detail):
        search = patch("places.work_enrichment.tmdb.search", return_value=candidates)
        get_detail = patch("places.work_enrichment.tmdb.get_detail", return_value=detail)
        return search, get_detail

    def test_fills_blank_fields_and_builds_poster_url(self):
        work = Work.objects.create(title="도깨비", category=Work.Category.DRAMA)
        search, get_detail = self._mock([_candidate(1, "도깨비")], _detail(1))
        with search, get_detail:
            status, filled = enrich_work(work)

        self.assertEqual(status, "matched")
        self.assertEqual(set(filled), {"description", "director", "release_date", "poster_url"})
        work.refresh_from_db()
        self.assertEqual(work.description, "줄거리입니다")
        self.assertEqual(work.director, "김감독")
        self.assertEqual(work.release_date, datetime.date(2016, 12, 2))
        self.assertEqual(work.poster_url, "https://image.tmdb.org/t/p/w500/abc.jpg")

    def test_does_not_overwrite_admin_filled_values_by_default(self):
        work = Work.objects.create(
            title="도깨비",
            category=Work.Category.DRAMA,
            description="관리자가 쓴 감성 줄거리",
            director="관리자입력 감독",
        )
        search, get_detail = self._mock([_candidate(1, "도깨비")], _detail(1))
        with search, get_detail:
            status, filled = enrich_work(work)

        self.assertEqual(status, "matched")
        self.assertEqual(set(filled), {"release_date", "poster_url"})
        work.refresh_from_db()
        self.assertEqual(work.description, "관리자가 쓴 감성 줄거리")
        self.assertEqual(work.director, "관리자입력 감독")

    def test_overwrite_flag_replaces_existing_values(self):
        work = Work.objects.create(
            title="도깨비", category=Work.Category.DRAMA, description="옛날 줄거리"
        )
        search, get_detail = self._mock([_candidate(1, "도깨비")], _detail(1))
        with search, get_detail:
            status, filled = enrich_work(work, overwrite=True)

        self.assertIn("description", filled)
        work.refresh_from_db()
        self.assertEqual(work.description, "줄거리입니다")

    def test_no_match_leaves_work_untouched(self):
        work = Work.objects.create(title="존재하지않는작품xyz", category=Work.Category.DRAMA)
        search, get_detail = self._mock([_candidate(1, "전혀다른작품")], _detail(1))
        with search, get_detail:
            status, filled = enrich_work(work)

        self.assertEqual(status, "no_match")
        self.assertEqual(filled, [])
        work.refresh_from_db()
        self.assertEqual(work.description, "")
        self.assertEqual(work.poster_url, "")

    def test_foreign_only_candidate_is_no_match_by_default(self):
        work = Work.objects.create(title="사랑에 관한 짧은 필름", category=Work.Category.MOVIE)
        candidates = [_candidate(31056, "사랑에 관한 짧은 필름", original_title="Krótki film o miłości", lang="pl")]
        search, get_detail = self._mock(candidates, _detail(31056))
        with search, get_detail:
            status, filled = enrich_work(work)

        self.assertEqual(status, "no_match")
        work.refresh_from_db()
        self.assertEqual(work.poster_url, "")

    def test_require_korean_false_enriches_foreign_work(self):
        work = Work.objects.create(title="사랑에 관한 짧은 필름", category=Work.Category.MOVIE)
        candidates = [_candidate(31056, "사랑에 관한 짧은 필름", original_title="Krótki film o miłości", lang="pl")]
        search, get_detail = self._mock(candidates, _detail(31056))
        with search, get_detail:
            status, filled = enrich_work(work, require_korean=False)

        self.assertEqual(status, "matched")
        work.refresh_from_db()
        self.assertTrue(work.poster_url)

    def test_matched_but_tmdb_values_empty_reports_no_change(self):
        work = Work.objects.create(title="도깨비", category=Work.Category.DRAMA)
        detail = _detail(1, overview="", director="", release_date="", poster_path=None)
        search, get_detail = self._mock([_candidate(1, "도깨비")], detail)
        with search, get_detail:
            status, filled = enrich_work(work)

        self.assertEqual(status, "matched_no_change")
        self.assertEqual(filled, [])

    def test_director_is_truncated_to_field_limit(self):
        work = Work.objects.create(title="도깨비", category=Work.Category.DRAMA)
        long_name = "가" * 250
        detail = _detail(1, director=long_name)
        search, get_detail = self._mock([_candidate(1, "도깨비")], detail)
        with search, get_detail:
            enrich_work(work)

        work.refresh_from_db()
        self.assertEqual(len(work.director), 100)

    def test_bad_release_date_string_is_skipped_not_crashed(self):
        work = Work.objects.create(title="도깨비", category=Work.Category.DRAMA)
        detail = _detail(1, release_date="날짜아님")
        search, get_detail = self._mock([_candidate(1, "도깨비")], detail)
        with search, get_detail:
            status, filled = enrich_work(work)

        self.assertEqual(status, "matched")
        self.assertNotIn("release_date", filled)
        work.refresh_from_db()
        self.assertIsNone(work.release_date)


@override_settings(TMDB_API_KEY="test-token", TMDB_IMAGE_BASE_URL="https://image.tmdb.org/t/p", TMDB_POSTER_SIZE="w500")
class EnrichWorksCommandTest(TestCase):
    def test_command_enriches_matches_and_survives_per_item_errors(self):
        ok = Work.objects.create(title="도깨비", category=Work.Category.DRAMA)
        broken = Work.objects.create(title="에러작품", category=Work.Category.MOVIE)
        missing = Work.objects.create(title="검색결과없음", category=Work.Category.DRAMA)

        def fake_search(title, category):
            if title == "도깨비":
                return [_candidate(1, "도깨비")]
            if title == "에러작품":
                raise RuntimeError("TMDB 통신 실패")
            return []

        with patch("places.work_enrichment.tmdb.search", side_effect=fake_search), patch(
            "places.work_enrichment.tmdb.get_detail", return_value=_detail(1)
        ):
            call_command("enrich_works_tmdb")

        ok.refresh_from_db()
        broken.refresh_from_db()
        missing.refresh_from_db()
        self.assertEqual(ok.poster_url, "https://image.tmdb.org/t/p/w500/abc.jpg")
        self.assertEqual(broken.poster_url, "")
        self.assertEqual(missing.poster_url, "")

    def test_only_missing_skips_already_filled_works(self):
        filled = Work.objects.create(
            title="도깨비",
            category=Work.Category.DRAMA,
            description="d",
            director="x",
            release_date=datetime.date(2016, 12, 2),
            poster_url="https://example.com/p.jpg",
        )

        with patch("places.work_enrichment.tmdb.search") as search:
            call_command("enrich_works_tmdb", only_missing=True)

        search.assert_not_called()
        filled.refresh_from_db()
        self.assertEqual(filled.poster_url, "https://example.com/p.jpg")
