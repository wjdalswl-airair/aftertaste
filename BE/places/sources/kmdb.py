"""한국영상자료원 KMDB(한국영화데이터베이스) Open API 호출.

작품(영화) 상세 정보를 가져온다. 실제 키로 호출해서 필드를 확인했다
(docs/DETAIL_SPEC.md 6-1 #28). 드라마 데이터는 이 API에 없다 — 영화 전용.
"""

import re

import requests
from django.conf import settings

_BASE_URL = "http://api.koreafilm.or.kr/openapi-data2/wisenut/search_api/search_json2.jsp"
_TIMEOUT_SECONDS = 10

# KMDB는 검색어와 일치하는 부분을 !HS...!HE로 감싸서 돌려준다. 화면에 보여줄 값이 아니라 걷어낸다.
_HIGHLIGHT_TAG_RE = re.compile(r"!HS|!HE")

# 배우 목록에 단역까지 수백 명이 들어있어서, 주연급만 main_cast에 담는다.
_MAIN_CAST_MAX_ACTORS = 6

# Work 필드 길이 제한을 넘으면 DB 저장이 실패한다 (places/models.py 참고). 잘라서 돌려준다.
_DIRECTOR_MAX_LENGTH = 100
_MAIN_CAST_MAX_LENGTH = 300
_POSTER_URL_MAX_LENGTH = 200


def _get_api_key():
    api_key = settings.KMDB_API_KEY
    if not api_key:
        raise RuntimeError("KMDB_API_KEY가 설정되지 않았습니다 (.env 확인).")
    return api_key


def _clean_title(raw_title):
    return " ".join(_HIGHLIGHT_TAG_RE.sub("", raw_title or "").split())


def _korean_plot(plots):
    for plot in (plots or {}).get("plot", []):
        if plot.get("plotLang") == "한국어" and plot.get("plotText"):
            return plot["plotText"]
    return ""


def _first_poster_url(posters):
    if not posters:
        return ""
    return posters.split("|")[0].strip()


def search_movies(*, title=None, director=None, keyword=None):
    """title/director/keyword 중 하나 이상으로 영화를 검색한다. 상세정보(줄거리·배우 등)까지 받아온다."""
    if not (title or director or keyword):
        raise ValueError("title, director, keyword 중 하나는 있어야 합니다.")

    params = {"collection": "kmdb_new2", "detail": "Y", "ServiceKey": _get_api_key()}
    if title:
        params["title"] = title
    if director:
        params["director"] = director
    if keyword:
        params["keyword"] = keyword

    response = requests.get(_BASE_URL, params=params, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()

    movies = [movie for collection in data.get("Data", []) for movie in collection.get("Result", [])]

    return [
        {
            "docid": movie.get("DOCID"),
            "title": _clean_title(movie.get("title")),
            "director": ", ".join(
                d.get("directorNm", "")
                for d in movie.get("directors", {}).get("director", [])
                if d.get("directorNm")
            )[:_DIRECTOR_MAX_LENGTH],
            "main_cast": ", ".join(
                a.get("actorNm", "")
                for a in movie.get("actors", {}).get("actor", [])[:_MAIN_CAST_MAX_ACTORS]
                if a.get("actorNm")
            )[:_MAIN_CAST_MAX_LENGTH],
            "release_date": movie.get("repRlsDate") or "",
            "poster_url": _first_poster_url(movie.get("posters"))[:_POSTER_URL_MAX_LENGTH],
            "description": _korean_plot(movie.get("plots")),
        }
        for movie in movies
    ]
