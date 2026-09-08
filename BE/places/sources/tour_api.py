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

import time
from urllib.parse import unquote

import requests
from django.conf import settings

_HOST = "https://apis.data.go.kr/B551011/KorService2"
_SEARCH_URL = f"{_HOST}/searchKeyword2"
_DETAIL_URL = f"{_HOST}/detailCommon2"
# data.go.kr 관광정보 API는 응답이 느리다 — 정상 호출도 8~10초가 예사라, 넉넉히 잡는다.
_TIMEOUT_SECONDS = 30

# data.go.kr은 초당 요청 수가 몰리면 HTTP 429(Too Many Requests)를 준다 — 일일 한도와는
# 별개다. 명소 수천 건을 이어서 호출하면 반드시 걸리므로, 429·5xx·타임아웃은 잠깐 쉬고
# 다시 시도한다. 그래도 안 되면 예외를 올려서 커맨드가 그 명소만 건너뛰게 한다.
# 재시도를 짧게 잡는 이유: 대량 실행에서 429가 지속되면 한 건에 오래 매달리기보다 빨리
# 건너뛰고 다음 실행(멱등)에서 다시 시도하는 편이 전체 처리량이 낫다.
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = (2, 5)
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# arrange=O : 대표이미지가 있는 항목을 먼저, 그 안에서 제목순. 우리는 이미지가 목적이라
# 이미지 없는 항목을 뒤로 미뤄서 numOfRows 안에 이미지 있는 후보가 최대한 들어오게 한다.
_ARRANGE_IMAGE_FIRST = "O"

# 키워드 하나당 받아올 후보 수. 동명이인 장소(예: "스타벅스")를 좌표로 걸러내려면
# 어느 정도 넉넉해야 하지만, 대표이미지 우선 정렬이라 앞쪽 30건이면 충분하다.
_NUM_OF_ROWS = 30

_MOBILE_OS = "ETC"
_MOBILE_APP = "aftertaste"


class TourApiDailyLimitError(RuntimeError):
    """일일 서비스 요청제한 횟수를 초과했다. 그날은 재시도해도 소용없으니 실행을 멈춰야 한다."""


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

    body = _call(
        _SEARCH_URL,
        {
            "numOfRows": _NUM_OF_ROWS,
            "pageNo": 1,
            "arrange": _ARRANGE_IMAGE_FIRST,
            "keyword": keyword,
        },
    )
    items = body.get("items")
    # 검색 결과가 없으면 items가 빈 문자열("")로 온다.
    if not items:
        return []

    rows = items.get("item", [])
    # 결과가 1건이면 리스트가 아니라 dict 하나로 오는 경우가 있다.
    if isinstance(rows, dict):
        rows = [rows]

    return [_normalize_item(row) for row in rows]


def get_detail(content_id):
    """관광정보 콘텐츠 하나의 대표 이미지·이름·주소·좌표를 가져온다 (detailCommon2).

    한 번 매칭해서 content_id를 알면(PlaceSource에 저장됨) 다시 이름으로 검색·매칭할
    필요 없이 이 함수로 최신 대표 이미지를 받는다. content_id가 유효하지 않으면 None.

    반환: search_keyword 후보와 같은 모양의 dict, 또는 None.
    """
    content_id = str(content_id or "").strip()
    if not content_id:
        return None

    body = _call(_DETAIL_URL, {"contentId": content_id})
    items = body.get("items")
    if not items:
        return None
    row = items.get("item", [])
    if isinstance(row, list):
        row = row[0] if row else None
    if not row:
        return None
    return _normalize_item(row)


def _call(url, extra_params):
    """TourAPI 한 곳을 호출하고 response.body를 돌려준다. 공통 파라미터·에러 처리 포함."""
    params = {
        "serviceKey": _get_service_key(),
        "MobileOS": _MOBILE_OS,
        "MobileApp": _MOBILE_APP,
        "_type": "json",
        **extra_params,
    }
    response = _get_with_retry(url, params)

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

    return data.get("response", {}).get("body", {})


def _get_with_retry(url, params):
    """TourAPI를 호출한다. 429·5xx·타임아웃이면 잠깐 쉬고 다시 시도한다.

    Retry-After 헤더가 있으면 그 값을, 없으면 _RETRY_BACKOFF_SECONDS를 따른다.
    재시도를 모두 소진하면 마지막 예외를 그대로 올린다.
    """
    last_exc = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            status = getattr(exc.response, "status_code", None)
            # 429 중에서도 "일일 한도 초과"면 재시도·이어서 호출 모두 의미 없다 — 바로 알린다.
            if status == 429 and _is_daily_limit(exc.response):
                raise TourApiDailyLimitError(
                    "TourAPI 일일 서비스 요청제한 횟수 초과 (자정 KST에 리셋)"
                ) from exc
            retryable = status in _RETRY_STATUS_CODES or isinstance(
                exc, (requests.ConnectionError, requests.Timeout)
            )
            if not retryable or attempt == _MAX_RETRIES:
                raise
            wait = _retry_after_seconds(exc) or _RETRY_BACKOFF_SECONDS[attempt]
            time.sleep(wait)
    raise last_exc  # 도달하지 않지만 방어적으로 둔다


def _is_daily_limit(response):
    """429 응답 본문이 "일일 요청제한 초과"인지 본다.

    본문은 JSON({"OpenAPI_ServiceResponse": {"cmmMsgHeader": {"errMsg":
    "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR", ...}}})이나 XML로 오는데,
    errMsg 문자열만 봐도 초당 제한(단순 429)과 구별된다.
    """
    if response is None:
        return False
    return "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in (response.text or "")


def _retry_after_seconds(exc):
    """HTTPError의 응답에 Retry-After 헤더(초 단위)가 있으면 float로, 없으면 None."""
    response = getattr(exc, "response", None)
    if response is None:
        return None
    try:
        return float(response.headers.get("Retry-After", ""))
    except ValueError:
        return None


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
