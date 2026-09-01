"""작품(Work)의 줄거리·감독·방영일자·포스터를 TMDB에서 채우는 서비스 계층.

여기서 하는 일 두 가지:
1. TMDB 검색 결과 중에서 "우리 Work와 같은 작품"을 가려낸다 (pick_tmdb_match).
   제목이 정확히 일치하는 후보만 인정한다 — 애매하면 채우지 않는다. Work는 KCISA
   촬영지 CSV에서 제목만 보고 만들어져서, 잘못 붙이면 엉뚱한 포스터가 걸린다.
   (예: "기생충"으로 검색하면 "기생충을 예방하자" 같은 교육영화가 섞여 나온다.)
2. 가려낸 작품의 상세정보를 Work에 반영한다. 관리자가 이미 채운 값은 덮어쓰지 않는다
   (Place가 공공데이터로 이름·주소만 채우고 설명·사진은 관리자 몫인 것과 같은 원칙).
   docs/DETAIL_SPEC.md 3장 註(2026-08-28): 작품 "설명"은 원래 관리자가 쓰는 감성적인
   줄거리 소개다. 그래서 TMDB 줄거리는 비어 있을 때 시작값으로만 넣고, 채워져 있으면
   건드리지 않는다 (--overwrite를 주면 그때만 덮어쓴다).

실제 TMDB 호출은 places/sources/tmdb.py에 있다. 이 모듈은 그 결과를 판단·저장만 한다.
"""

import datetime
import logging

from django.conf import settings

from places.sources import tmdb

logger = logging.getLogger(__name__)

# TMDB가 채우는 Work 필드들. 전부 "비어 있을 때만 채운다"가 기본 규칙이다.
# (커맨드의 --only-missing 필터도 이 목록을 기준으로 삼는다.)
FILLABLE_FIELDS = ("description", "director", "release_date", "poster_url")

# Work.director는 CharField(max_length=100). 넘치면 저장이 실패하므로 잘라 넣는다
# (translation.py의 제목 자르기, services.py의 _WORK_TITLE_MAX_LENGTH 처리와 같은 방식).
_DIRECTOR_MAX_LENGTH = 100

# 우리 Work에 방영일자가 이미 있는 경우, TMDB 후보와 연도가 이만큼 넘게 차이 나면
# 다른 작품으로 본다. 재방영·해외 개봉 지연을 감안해 1년까지는 같은 작품으로 인정한다.
_YEAR_TOLERANCE = 1

# 제목 비교 시 지우는 문자. 괄호·구두점·공백처럼 표기만 다르고 뜻은 같은 것들.
_TITLE_NOISE_CHARS = set(" \t　()[]{}<>「」『』:;,.·・…!?\"'`~-–—/\\")


def normalize_title_for_match(title):
    """제목 비교용으로 정규화한다. 공백·괄호·구두점을 모두 지우고 소문자로 만든다.

    "(아는 건 별로 없지만) 가족입니다" 와 "아는 건 별로 없지만 가족입니다" 를 같은 것으로,
    "Parasite" 와 "parasite" 를 같은 것으로 본다.
    """
    return "".join(ch for ch in (title or "").casefold() if ch not in _TITLE_NOISE_CHARS)


def pick_tmdb_match(work_title, work_release_date, candidates, *, require_korean=True):
    """TMDB 검색 후보 중 우리 작품과 같은 것을 하나 고른다. 없으면 None.

    규칙:
      1. 정규화한 제목이 후보의 표시 제목 또는 원어 제목과 정확히 같아야 한다.
         (부분 일치·유사도는 인정하지 않는다 — 틀린 매칭이 빈 값보다 나쁘다.)
      2. require_korean이면 원어가 한국어(original_language == "ko")인 후보만 인정한다.
         우리 Work는 국내 촬영지 데이터(KCISA)에서 왔으니 사실상 전부 한국 제작물이다.
         한국어 제목이 우연히 똑같은 외국 작품(예: 폴란드 영화 "사랑에 관한 짧은 필름")이
         걸리는 것을 막는다 — 그런 건 빈 값으로 두는 게 낫다.
      3. 우리 Work에 방영일자가 있으면, 후보 연도가 ±1년 안에 들어야 한다.
      4. 남은 후보가 여럿이면: 인기 점수가 높은 것.
    """
    target = normalize_title_for_match(work_title)
    if not target:
        return None

    work_year = work_release_date.year if work_release_date else None

    matched = []
    for candidate in candidates:
        titles = {
            normalize_title_for_match(candidate.get("title")),
            normalize_title_for_match(candidate.get("original_title")),
        }
        if target not in titles:
            continue
        if require_korean and candidate.get("original_language") != "ko":
            continue
        if work_year is not None and candidate.get("release_year") is not None:
            if abs(candidate["release_year"] - work_year) > _YEAR_TOLERANCE:
                continue
        matched.append(candidate)

    if not matched:
        return None

    matched.sort(key=lambda c: c.get("popularity") or 0.0, reverse=True)
    return matched[0]


def _parse_release_date(date_str):
    """'YYYY-MM-DD' 문자열을 date로 바꾼다. 형식이 아니면 None."""
    try:
        return datetime.date.fromisoformat((date_str or "").strip())
    except ValueError:
        return None


def _build_poster_url(poster_path):
    """TMDB poster_path('/xxx.jpg') 앞에 CDN 주소를 붙여 완전한 URL로 만든다. 없으면 빈 문자열."""
    if not poster_path:
        return ""
    return f"{settings.TMDB_IMAGE_BASE_URL}/{settings.TMDB_POSTER_SIZE}{poster_path}"


def _values_from_detail(detail):
    """TMDB 상세 dict를 Work 필드 이름 → 저장할 값 dict로 바꾼다. 빈 값은 담지 않는다."""
    values = {}

    if detail.get("overview"):
        values["description"] = detail["overview"]

    if detail.get("director"):
        values["director"] = detail["director"][:_DIRECTOR_MAX_LENGTH]

    release_date = _parse_release_date(detail.get("release_date"))
    if release_date is not None:
        values["release_date"] = release_date

    poster_url = _build_poster_url(detail.get("poster_path"))
    if poster_url:
        values["poster_url"] = poster_url

    return values


def _is_blank(value):
    return value is None or value == ""


def enrich_work(work, *, overwrite=False, require_korean=True):
    """Work 하나를 TMDB 정보로 보강해서 저장한다.

    반환: (status, filled_fields)
      status:
        "matched"          - TMDB에서 같은 작품을 찾아 한 개 이상 필드를 채웠다
        "matched_no_change" - 같은 작품은 찾았지만 채울 게 없었다(이미 다 있거나 TMDB도 빈 값)
        "no_match"         - 같은 작품을 못 찾았다 (제목이 정확히 일치하는 후보 없음)
        "unsupported"      - category가 DRAMA/MOVIE가 아니라 TMDB에서 찾을 수 없다
      filled_fields: 이번에 실제로 값이 바뀐 Work 필드 이름 리스트

    통신 오류·타임아웃 등 예외는 그대로 올린다 (호출하는 커맨드가 건별로 잡아서 계속 돈다).
    """
    if tmdb.category_to_media_type(work.category) is None:
        return "unsupported", []

    candidates = tmdb.search(work.title, work.category)
    match = pick_tmdb_match(work.title, work.release_date, candidates, require_korean=require_korean)
    if match is None:
        return "no_match", []

    detail = tmdb.get_detail(match["tmdb_id"], work.category)
    values = _values_from_detail(detail)

    filled = []
    for field in FILLABLE_FIELDS:
        if field not in values:
            continue
        if not overwrite and not _is_blank(getattr(work, field)):
            continue
        if getattr(work, field) == values[field]:
            continue
        setattr(work, field, values[field])
        filled.append(field)

    if filled:
        work.save(update_fields=filled)
        return "matched", filled

    return "matched_no_change", []
