"""카카오맵 지오코딩 — 장소명 텍스트를 좌표로 바꾼다.

경기 데이터 드림은 좌표 없이 장소명 텍스트만 주기 때문에 필요하다
(docs/DETAIL_SPEC.md 7장 #1 참고).

주소 검색 API(/v2/local/search/address.json)는 정식 주소만 인식해서 "경복궁" 같은
장소명을 넣으면 결과가 0건이다 (실제 호출로 확인). 대신 장소명을 검색할 수 있는
키워드 검색 API(/v2/local/search/keyword.json)를 쓴다.
"""

import requests
from django.conf import settings

_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
_CATEGORY_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/category.json"
_TIMEOUT_SECONDS = 10


def _get_headers():
    api_key = settings.KAKAO_API_KEY
    if not api_key:
        raise RuntimeError("KAKAO_API_KEY가 설정되지 않았습니다 (.env 확인).")
    return {"Authorization": f"KakaoAK {api_key}"}


def search_place(query, size=15, x=None, y=None, radius=None):
    """장소명으로 검색해서 후보 목록을 가져온다. 가까운 순서가 아니라 카카오 자체 정렬 순서다.

    x(경도)·y(위도)·radius(미터)를 함께 주면 그 좌표 주변으로 검색 범위를 좁힌다
    (명소 상세의 "주변 상권" 조회에 쓰인다). 기존처럼 query만 주면 지오코딩 용도로
    그대로 동작한다.
    """
    params = {"query": query, "size": size}
    if x is not None and y is not None:
        params["x"] = x
        params["y"] = y
        if radius is not None:
            params["radius"] = radius

    response = requests.get(
        _KEYWORD_SEARCH_URL, params=params, headers=_get_headers(), timeout=_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "place_name": doc.get("place_name"),
            "address_name": doc.get("address_name"),
            "road_address_name": doc.get("road_address_name"),
            "latitude": float(doc["y"]),
            "longitude": float(doc["x"]),
            "category_name": doc.get("category_name"),
        }
        for doc in data.get("documents", [])
    ]


def search_by_category(category_group_code, x, y, radius, size=15):
    """카테고리 코드 기준으로 좌표 주변 장소를 찾는다 (카카오 카테고리 검색 API).

    키워드 검색과 달리 검색어(query) 없이 category_group_code + x(경도)·y(위도)·radius(미터)만으로
    찾는다. 명소 상세의 "주변 상권" 조회에서 음식점(FD6)·카페(CE7)·관광명소(AT4) 등을 가져올 때 쓴다
    (PHASES/PHASE2.md 2-5 "주변 상권 검색 기준").
    """
    params = {"category_group_code": category_group_code, "x": x, "y": y, "radius": radius, "size": size}

    response = requests.get(
        _CATEGORY_SEARCH_URL, params=params, headers=_get_headers(), timeout=_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    data = response.json()

    return [
        {
            "id": doc.get("id"),
            "place_name": doc.get("place_name"),
            "address_name": doc.get("address_name"),
            "road_address_name": doc.get("road_address_name"),
            "latitude": float(doc["y"]),
            "longitude": float(doc["x"]),
            "category_name": doc.get("category_name"),
        }
        for doc in data.get("documents", [])
    ]


def geocode(query):
    """장소명으로 검색해서 가장 첫 번째 결과의 좌표만 돌려준다. 결과가 없으면 None."""
    results = search_place(query, size=1)
    if not results:
        return None
    return results[0]["latitude"], results[0]["longitude"]
