"""한국관광공사 TourAPI(국문 관광정보 서비스_GW) 호출 — 키워드 검색(searchKeyword2).

등록된 관광지·음식점·문화시설의 대표 이미지(firstimage)를 명소(Place.photo_url)에
채우는 데 쓴다. 좌표(mapx=경도, mapy=위도)와 주소도 함께 주므로, 어떤 검색 결과가
우리 Place와 같은 장소인지 가려낼 때 쓴다. "무엇이 같은 장소인지" 판단은 이 모듈이
아니라 places/place_photo_enrichment.py에서 다룬다 (tmdb.py ↔ work_enrichment.py 관계와 같다).

serviceKey는 공공데이터포털에서 받은 "디코딩된 일반 인증키"를 그대로 넣는다 —
requests가 쿼리스트링을 인코딩하므로, 이미 URL 인코딩된 키를 넣으면 이중 인코딩돼
SERVICE_KEY_IS_NOT_REGISTERED_ERROR가 난다.

여기서는 API를 그대로 호출해서 필요한 값만 추린 dict 리스트를 돌려주고, 실패하면
예외를 그대로 올린다 (호출하는 커맨드가 건별로 잡아서 계속 돈다).
"""

from urllib.parse import unquote

import requests
from django.conf import settings

_BASE_URL = "https://apis.data.go.kr/B551011/KorService2/searchKeyword2"
_TIMEOUT_SECONDS = 10

# arrange=O : 대표이미지가 있는 항목을 먼저, 그 안에서 제목순. 우리는 이미지가 목적이라
# 이미지 없는 항목을 뒤로 미뤄서 numOfRows 안에 이미지 있는 후보가 최대한 들어오게 한다.
_ARRANGE_IMAGE_FIRST = "O"

# 키워드 하나당 받아올 후보 수. 동명이인 장소(예: "스타벅스")를 좌표로 걸러내려면
# 어느 정도 넉넉해야 하지만, 대표이미지 우선 정렬이라 앞쪽 30건이면 충분하다.
_NUM_OF_ROWS = 30

_MOBILE_OS = "ETC"
_MOBILE_APP = "aftertaste"


def _get_service_key():
    service_key = settings.TOUR_API_KEY
    if not service_key:
        raise RuntimeError("TOUR_API_KEY가 설정되지 않았습니다 (.env 확인).")
    # 공공데이터포털은 "인코딩된 인증키"와 "디코딩된 인증키" 두 가지를 준다. 인코딩된 키
    # (%2B, %2F, %3D 포함)를 그대로 넣으면 requests가 %를 다시 인코딩(%252B)해서 403이 난다.
    # 어느 쪽을 넣든 동작하도록, 이미 인코딩돼 보이면 원래 값으로 되돌린다.
    if "%" in service_key:
        return unquote(service_key)
    return service_key


def search_keyword(keyword):
    """장소 이름으로 관광정보 후보 목록을 가져온다.

    반환: 후보 dict 리스트. 각 dict는 아래 키를 가진다.
      - content_id: 관광정보 콘텐츠 번호
      - content_type_id: 콘텐츠 종류(12=관광지, 39=음식점 등)
      - title: 장소 이름
      - address: 주소(addr1 + addr2)
      - latitude / longitude: 위경도(float) 또는 None
      - first_image: 대표 이미지 URL(firstimage, 없으면 firstimage2). 둘 다 없으면 ""
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    params = {
        "serviceKey": _get_service_key(),
        "numOfRows": _NUM_OF_ROWS,
        "pageNo": 1,
        "MobileOS": _MOBILE_OS,
        "MobileApp": _MOBILE_APP,
        "_type": "json",
        "arrange": _ARRANGE_IMAGE_FIRST,
        "keyword": keyword,
    }

    response = requests.get(_BASE_URL, params=params, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        # 인증키 오류 등은 _type=json이어도 XML 에러 문서로 돌아온다.
        raise RuntimeError(f"TourAPI 응답을 JSON으로 읽을 수 없습니다: {response.text[:300]}")

    # 파라미터·인증 오류는 {"resultCode": "10", "resultMsg": "..."}처럼 평평한 문서로 온다.
    if "response" not in data:
        raise RuntimeError(f"TourAPI 오류: {data.get('resultCode')} {data.get('resultMsg', data)}")

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") not in ("0000", None):
        raise RuntimeError(f"TourAPI 오류: {header.get('resultCode')} {header.get('resultMsg')}")

    body = data.get("response", {}).get("body", {})
    items = body.get("items")
    # 검색 결과가 없으면 items가 빈 문자열("")로 온다.
    if not items:
        return []

    rows = items.get("item", [])
    # 결과가 1건이면 리스트가 아니라 dict 하나로 오는 경우가 있다.
    if isinstance(rows, dict):
        rows = [rows]

    return [_normalize_item(row) for row in rows]


def _normalize_item(row):
    address = " ".join(part for part in (row.get("addr1"), row.get("addr2")) if part).strip()
    return {
        "content_id": row.get("contentid"),
        "content_type_id": row.get("contenttypeid"),
        "title": row.get("title") or "",
        "address": address,
        "latitude": _to_float(row.get("mapy")),
        "longitude": _to_float(row.get("mapx")),
        "first_image": row.get("firstimage") or row.get("firstimage2") or "",
    }


def _to_float(value):
    """mapx/mapy 문자열을 float로 바꾼다. 값이 없거나("", "0") 숫자가 아니면 None."""
    if value in (None, "", "0"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed != 0.0 else None
