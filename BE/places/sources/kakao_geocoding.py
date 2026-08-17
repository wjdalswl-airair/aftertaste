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
_TIMEOUT_SECONDS = 10


def _get_headers():
    api_key = settings.KAKAO_API_KEY
    if not api_key:
        raise RuntimeError("KAKAO_API_KEY가 설정되지 않았습니다 (.env 확인).")
    return {"Authorization": f"KakaoAK {api_key}"}


def search_place(query, size=15):
    """장소명으로 검색해서 후보 목록을 가져온다. 가까운 순서가 아니라 카카오 자체 정렬 순서다."""
    params = {"query": query, "size": size}

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


def geocode(query):
    """장소명으로 검색해서 가장 첫 번째 결과의 좌표만 돌려준다. 결과가 없으면 None."""
    results = search_place(query, size=1)
    if not results:
        return None
    return results[0]["latitude"], results[0]["longitude"]
