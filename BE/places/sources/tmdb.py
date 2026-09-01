"""TMDB(The Movie Database) API 호출.

작품(영화·드라마)의 줄거리·감독·방영일자·포스터를 가져온다. 실제 토큰으로 호출해서
필드를 확인했다. 인증은 "Authorization: Bearer <읽기 액세스 토큰>" 헤더로 한다
(짧은 v3 api_key 쿼리 방식이 아니다 — 그렇게 부르면 401이 난다).

여기서는 API를 그대로 호출해서 필요한 값만 추린 dict를 돌려주고, 실패하면 예외를
그대로 올린다. "어떤 검색 결과가 우리 Work와 같은 작품인지" 판단하는 규칙은 이 모듈이
아니라 places/work_enrichment.py에서 다룬다 (google_translate.py ↔ translation.py 관계와 같다).
"""

import requests
from django.conf import settings

_BASE_URL = "https://api.themoviedb.org/3"
_TIMEOUT_SECONDS = 10

# 검색·상세를 어느 언어로 받을지. 한국어 줄거리·제목을 우선 받는다. 한국어 번역이 없는
# 작품이면 TMDB가 알아서 원어(대개 영어) 값을 준다.
_LANGUAGE = "ko-KR"

# Work.category → TMDB 미디어 종류. 드라마는 TV 시리즈로, 영화는 movie로 찾는다.
_CATEGORY_TO_MEDIA = {"DRAMA": "tv", "MOVIE": "movie"}


def category_to_media_type(category):
    """Work.category("DRAMA"/"MOVIE") 문자열을 TMDB 미디어 종류("tv"/"movie")로 바꾼다.

    아는 값이 아니면 None. 호출하는 쪽이 이걸로 "TMDB에서 찾을 수 있는 작품인지" 판단한다.
    """
    return _CATEGORY_TO_MEDIA.get((category or "").strip().upper())


def _headers():
    token = settings.TMDB_API_KEY
    if not token:
        raise RuntimeError("TMDB_API_KEY가 설정되지 않았습니다 (.env 확인).")
    return {"Authorization": f"Bearer {token}", "accept": "application/json"}


def search(title, category):
    """제목으로 작품 후보 목록을 가져온다.

    category가 DRAMA면 TV 시리즈를, MOVIE면 영화를 검색한다. 결과는 TMDB가 인기순으로
    정렬해서 준다. 어떤 후보가 우리 작품과 같은지는 호출하는 쪽에서 제목·연도로 가린다.

    반환: 후보 dict 리스트. 각 dict는 아래 키를 가진다.
      - tmdb_id: TMDB 작품 번호
      - title: 표시 제목(요청 언어 기준)
      - original_title: 원어 제목
      - original_language: 원어 코드(예: "ko")
      - release_year: 방영/개봉 연도(int) 또는 None
      - popularity: TMDB 인기 점수(float)
    """
    media_type = category_to_media_type(category)
    if media_type is None:
        return []

    params = {"query": title, "language": _LANGUAGE, "include_adult": "false", "page": 1}
    response = requests.get(
        f"{_BASE_URL}/search/{media_type}", headers=_headers(), params=params, timeout=_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    return [_normalize_search_result(item, media_type) for item in results]


def get_detail(tmdb_id, category):
    """작품 하나의 상세정보를 가져온다 (줄거리·감독·방영일자·포스터).

    반환: 아래 키를 가진 dict.
      - tmdb_id
      - overview: 줄거리(요청 언어 기준, 없으면 빈 문자열)
      - director: 감독/연출 이름. 여러 명이면 ", "로 이어 붙인다. 없으면 빈 문자열
      - release_date: "YYYY-MM-DD" 문자열 또는 빈 문자열
      - poster_path: "/xxxx.jpg" 또는 None (CDN 주소 앞부분은 붙어 있지 않다)
    """
    media_type = category_to_media_type(category)
    if media_type is None:
        raise ValueError(f"TMDB에서 찾을 수 없는 category입니다: {category!r}")

    params = {"language": _LANGUAGE, "append_to_response": "credits"}
    response = requests.get(
        f"{_BASE_URL}/{media_type}/{tmdb_id}", headers=_headers(), params=params, timeout=_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()

    return {
        "tmdb_id": tmdb_id,
        "overview": (data.get("overview") or "").strip(),
        "director": _extract_director(data, media_type),
        "release_date": (data.get("first_air_date") if media_type == "tv" else data.get("release_date")) or "",
        "poster_path": data.get("poster_path"),
    }


def _normalize_search_result(item, media_type):
    if media_type == "tv":
        display_title = item.get("name") or ""
        original_title = item.get("original_name") or ""
        date_str = item.get("first_air_date") or ""
    else:
        display_title = item.get("title") or ""
        original_title = item.get("original_title") or ""
        date_str = item.get("release_date") or ""

    return {
        "tmdb_id": item.get("id"),
        "title": display_title,
        "original_title": original_title,
        "original_language": item.get("original_language") or "",
        "release_year": _year_from_date(date_str),
        "popularity": item.get("popularity") or 0.0,
    }


def _extract_director(data, media_type):
    """상세 응답에서 감독/연출 이름을 뽑는다.

    TV 시리즈: 먼저 created_by(제작·기획)를 보고, 없으면 credits.crew의 Director를 본다.
    영화: credits.crew에서 job이 "Director"인 사람.
    한국 드라마는 연출(PD)이 crew에 잘 안 들어와서 created_by가 그나마 가깝다.
    """
    names = []

    if media_type == "tv":
        names = [person.get("name") for person in data.get("created_by", []) if person.get("name")]

    if not names:
        crew = data.get("credits", {}).get("crew", [])
        names = [person.get("name") for person in crew if person.get("job") == "Director" and person.get("name")]

    # 같은 이름이 중복으로 들어오는 경우가 있어서 순서를 지키며 한 번씩만 남긴다.
    seen = set()
    unique = [name for name in names if not (name in seen or seen.add(name))]
    return ", ".join(unique)


def _year_from_date(date_str):
    """'YYYY-MM-DD' 또는 'YYYY...' 문자열에서 연도(int)만 뽑는다. 못 뽑으면 None."""
    if not date_str or len(date_str) < 4 or not date_str[:4].isdigit():
        return None
    return int(date_str[:4])
