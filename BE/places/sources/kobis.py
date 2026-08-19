"""영화진흥위원회(KOBIS) Open API 호출.

작품(영화) 정보를 가져온다. 실제 키로 호출해서 필드를 확인했다
(docs/DETAIL_SPEC.md 7장 #1 참고). 관객수는 이 API에 없다 —
별도의 박스오피스 API(searchWeeklyBoxOfficeList 등)에서 제공한다.
"""

import requests
from django.conf import settings

_BASE_URL = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/movie"
_TIMEOUT_SECONDS = 10


def _get_api_key():
    api_key = settings.KOBIS_API_KEY
    if not api_key:
        raise RuntimeError("KOBIS_API_KEY가 설정되지 않았습니다 (.env 확인).")
    return api_key


def search_movie_list(movie_name=None, open_start_dt=None, open_end_dt=None, cur_page=1, item_per_page=10):
    """조건에 맞는 영화 목록을 가져온다. movie_name 등을 안 주면 최신순 전체 목록을 페이지 단위로 준다."""
    params = {
        "key": _get_api_key(),
        "curPage": cur_page,
        "itemPerPage": item_per_page,
    }
    if movie_name:
        params["movieNm"] = movie_name
    if open_start_dt:
        params["openStartDt"] = open_start_dt
    if open_end_dt:
        params["openEndDt"] = open_end_dt

    response = requests.get(f"{_BASE_URL}/searchMovieList.json", params=params, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()

    result = data.get("movieListResult", {})
    movies = result.get("movieList", [])

    return {
        "total_count": result.get("totCnt", 0),
        "movies": [
            {
                "movie_cd": movie.get("movieCd"),
                "movie_nm": movie.get("movieNm"),
                "movie_nm_en": movie.get("movieNmEn"),
                "prdt_year": movie.get("prdtYear"),
                "open_dt": movie.get("openDt"),
                "director_names": [d.get("peopleNm") for d in movie.get("directors", [])],
            }
            for movie in movies
        ],
    }


def get_movie_info(movie_cd):
    """영화 하나의 상세정보를 가져온다 (배우/감독/장르/관람등급 등). 관객수는 포함되지 않는다."""
    params = {"key": _get_api_key(), "movieCd": movie_cd}

    response = requests.get(f"{_BASE_URL}/searchMovieInfo.json", params=params, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()

    movie_info = data.get("movieInfoResult", {}).get("movieInfo")
    if movie_info is None:
        raise RuntimeError(f"KOBIS에서 movieCd={movie_cd}에 대한 정보를 찾지 못했습니다.")

    watch_grades = [audit.get("watchGradeNm") for audit in movie_info.get("audits", [])]

    return {
        "movie_cd": movie_info.get("movieCd"),
        "movie_nm": movie_info.get("movieNm"),
        "movie_nm_en": movie_info.get("movieNmEn"),
        "show_tm": movie_info.get("showTm"),
        "prdt_year": movie_info.get("prdtYear"),
        "open_dt": movie_info.get("openDt"),
        "nations": [n.get("nationNm") for n in movie_info.get("nations", [])],
        "genres": [g.get("genreNm") for g in movie_info.get("genres", [])],
        "director_names": [d.get("peopleNm") for d in movie_info.get("directors", [])],
        "actor_names": [a.get("peopleNm") for a in movie_info.get("actors", [])],
        "watch_grade": watch_grades[0] if watch_grades else None,
    }
