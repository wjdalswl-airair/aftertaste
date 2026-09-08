"""한국어 위키백과(ko.wikipedia.org) API 호출 — 문서 대표 이미지(pageimages).

TourAPI는 등록된 관광지·음식점 위주라 카페·궁·유적 등 위키백과에만 있는 명소를 못 채운다.
그런 명소의 대표 사진(Place.photo_url)을 위키백과 문서의 대표 이미지로 보강하는 데 쓴다.
TourAPI와 달리 호출 한도가 없고 인증키도 필요 없다.

문서에 좌표(coordinates)가 있으면 함께 주므로, 어떤 검색 결과가 우리 Place와 같은
장소인지 가려낼 때 쓴다. "무엇이 같은 장소인지" 판단은 이 모듈이 아니라
places/place_photo_enrichment.py에서 한다 (tour_api.py ↔ place_photo_enrichment.py 관계와 같다).

대표 이미지는 위키미디어 커먼즈 파일만 쓴다(_photo_url 참고). 커먼즈 파일은 자유
라이선스(CC-BY / CC-BY-SA / 퍼블릭도메인)라, 지금은 URL만 저장하고 상업적 사용 시
저작자 표시가 필요하다 (docs/DETAIL_SPEC.md 6-1 #31).

여기서는 API를 그대로 호출해서 필요한 값만 추린 dict 리스트를 돌려주고, 실패하면
예외를 그대로 올린다 (호출하는 커맨드가 건별로 잡아서 계속 돈다).
"""

import time
from urllib.parse import unquote, urlsplit, urlunsplit

import requests

_API_URL = "https://ko.wikipedia.org/w/api.php"
_TIMEOUT_SECONDS = 15

# 위키미디어는 앱을 식별할 수 있는 User-Agent를 요구한다 (없으면 차단될 수 있음).
# https://meta.wikimedia.org/wiki/User-Agent_policy
# HTTP 헤더는 latin-1만 담을 수 있어 한글을 넣으면 requests가 인코딩 에러를 낸다 — 영문으로 둔다.
_HEADERS = {
    "User-Agent": "aftertaste/1.0 (film-location tour service; "
    "https://github.com/wjdalswl-airair/aftertaste) python-requests"
}

# 429(Too Many Requests)·5xx·타임아웃이면 잠깐 쉬고 다시 시도한다. 저용량이라 거의 안 걸리지만
# 명소 수천 건을 이어서 돌리므로 방어적으로 둔다. TourAPI와 달리 일일 한도는 없다.
_MAX_RETRIES = 2
_RETRY_BACKOFF_SECONDS = (2, 5)
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

# 검색어 하나당 받아올 문서 수. 대표 이미지 우선이 아니라 검색 적합도 순이라, 동명 문서를
# 좌표로 걸러낼 수 있게 어느 정도 넉넉히 잡는다.
_SEARCH_LIMIT = 20

# pageimages가 사진 대신 로고·문장(紋章)·지도를 대표 이미지로 주는 경우가 있어 걸러낸다.
# SVG는 거의 다 로고·도표라 확장자로, 그 외는 파일 이름의 낱말로 판단한다.
_NON_PHOTO_SUFFIXES = (".svg",)
_NON_PHOTO_NAME_HINTS = (
    "logo",
    "emblem",
    "wordmark",
    "coat_of_arms",
    "flag_of",
    "seal_of",
    "locator",
    "_map",
    "map_of",
)

# 대표 이미지 중 "commons"(위키미디어 커먼즈)에 올라온 것만 쓴다. 커먼즈 파일은 자유
# 라이선스(CC-BY / CC-BY-SA / 퍼블릭도메인)라 저작자 표시만 하면 상업적 사용이 가능하다.
# 반면 upload.wikimedia.org/wikipedia/ko/ 경로는 한국어 위키백과에 개별 업로드된 파일로,
# 대부분 "공정 이용(fair use)"이라 위키백과 밖에서는 못 쓴다 — 이런 URL은 버린다.
_ALLOWED_IMAGE_PATH = "/wikipedia/commons/"


def search_keyword(keyword):
    """문서 제목으로 위키백과를 검색해 후보 목록을 가져온다.

    반환: 후보 dict 리스트. tour_api.search_keyword와 같은 모양이다.
      - content_id: 문서 번호(pageid, 문자열)
      - content_type_id: 항상 None (위키백과엔 콘텐츠 종류가 없다)
      - title: 문서 제목
      - address: 항상 "" (위키백과는 주소를 주지 않는다)
      - latitude / longitude: 문서 좌표(float) 또는 None
      - first_image: 대표 이미지 URL(pageimages original). 없거나 사진이 아니면 ""
    """
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    body = _call(
        {
            "generator": "search",
            "gsrsearch": keyword,
            "gsrnamespace": 0,
            "gsrlimit": _SEARCH_LIMIT,
            "prop": "pageimages|coordinates",
            "piprop": "original",
            # generator와 함께 쓸 때 pilimit을 안 주면 첫 문서에만 이미지가 붙는다.
            "pilimit": "max",
            "colimit": "max",
        }
    )
    pages = body.get("query", {}).get("pages", [])
    return [_normalize_page(page) for page in pages]


def get_detail(page_id):
    """문서 하나의 대표 이미지·제목·좌표를 문서 번호(pageid)로 바로 가져온다.

    한 번 매칭해서 pageid를 알면(PlaceSource에 저장됨) 다시 제목으로 검색·매칭할 필요
    없이 이 함수로 최신 대표 이미지를 받는다. pageid가 유효하지 않으면 None.
    """
    page_id = str(page_id or "").strip()
    if not page_id:
        return None

    body = _call(
        {
            "pageids": page_id,
            "prop": "pageimages|coordinates",
            "piprop": "original",
            "colimit": "max",
        }
    )
    pages = body.get("query", {}).get("pages", [])
    page = next((p for p in pages if not p.get("missing")), None)
    return _normalize_page(page) if page else None


def _call(extra_params):
    """위키백과 API를 호출하고 response 본문(dict)을 돌려준다. 공통 파라미터·에러 처리 포함."""
    params = {
        "action": "query",
        "format": "json",
        "formatversion": 2,
        **extra_params,
    }
    response = _get_with_retry(params)

    try:
        data = response.json()
    except ValueError:
        raise RuntimeError(f"위키백과 응답을 JSON으로 읽을 수 없습니다: {response.text[:300]}")

    if "error" in data:
        error = data["error"]
        raise RuntimeError(f"위키백과 API 오류: {error.get('code')} {error.get('info', error)}")

    return data


def _get_with_retry(params):
    """위키백과 API를 호출한다. 429·5xx·타임아웃이면 잠깐 쉬고 다시 시도한다."""
    last_exc = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = requests.get(
                _API_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            status = getattr(exc.response, "status_code", None)
            retryable = status in _RETRY_STATUS_CODES or isinstance(
                exc, (requests.ConnectionError, requests.Timeout)
            )
            if not retryable or attempt == _MAX_RETRIES:
                raise
            time.sleep(_RETRY_BACKOFF_SECONDS[attempt])
    raise last_exc  # 도달하지 않지만 방어적으로 둔다


def _normalize_page(page):
    coordinate = (page.get("coordinates") or [{}])[0]
    return {
        "content_id": str(page.get("pageid")) if page.get("pageid") is not None else None,
        "content_type_id": None,
        "title": page.get("title") or "",
        "address": "",
        "latitude": _to_float(coordinate.get("lat")),
        "longitude": _to_float(coordinate.get("lon")),
        "first_image": _photo_url((page.get("original") or {}).get("source")),
    }


def _photo_url(source):
    """pageimages가 준 대표 이미지 URL을 정리한다. 쓸 수 없으면 "".

    - API가 붙이는 추적용 쿼리스트링(?utm_source=...)을 뗀다.
    - 커먼즈(자유 라이선스) 파일이 아니거나 SVG(로고·지도)면 버린다.
    """
    source = (source or "").strip()
    if not source:
        return ""
    parts = urlsplit(source)
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    if _ALLOWED_IMAGE_PATH not in clean:
        return ""
    # 파일 이름은 URL 인코딩(%EA%B3%84...)돼 있어 낱말 비교 전에 되돌린다.
    name = unquote(parts.path.rsplit("/", 1)[-1]).lower()
    if name.endswith(_NON_PHOTO_SUFFIXES) or any(hint in name for hint in _NON_PHOTO_NAME_HINTS):
        return ""
    return clean


def _to_float(value):
    """좌표 문자열/숫자를 float로 바꾼다. 값이 없거나 숫자가 아니면 None."""
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
