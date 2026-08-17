"""경기 데이터 드림 Open API 호출 — "촬영지원 현황" 데이터셋.

시군명·작품명·촬영구분명·촬영연도·촬영장소명을 준다. 좌표는 없다 — 카카오 지오코딩으로
따로 좌표를 구해야 한다 (kakao_geocoding.py, docs/DETAIL_SPEC.md 7장 #1 참고).

주의: User-Agent 헤더 없이 호출하면 "보안 정책에 의해 접근이 차단되었습니다" 라는
에러 페이지(HTML)가 돌아온다. 실제 호출로 확인한 내용이라 헤더를 반드시 넣는다.
"""

import requests
from django.conf import settings

_BASE_URL = "https://openapi.gg.go.kr/PhotographySupport"
_TIMEOUT_SECONDS = 10
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _get_api_key():
    api_key = settings.GYEONGGI_DATA_DREAM_API_KEY
    if not api_key:
        raise RuntimeError("GYEONGGI_DATA_DREAM_API_KEY가 설정되지 않았습니다 (.env 확인).")
    return api_key


def fetch_photography_support(page_index=1, page_size=100):
    """촬영지원 현황 목록을 한 페이지 가져온다."""
    params = {
        "KEY": _get_api_key(),
        "Type": "json",
        "pIndex": page_index,
        "pSize": page_size,
    }

    response = requests.get(_BASE_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()

    sections = data.get("PhotographySupport")
    if sections is None:
        # 인증키 오류 등으로 데이터 없이 RESULT만 오는 경우.
        result = data.get("RESULT", {})
        raise RuntimeError(f"경기데이터드림 API 오류: {result.get('MESSAGE', data)}")

    head = next((s["head"] for s in sections if "head" in s), [])
    result = next((h["RESULT"] for h in head if "RESULT" in h), {})
    if result.get("CODE") != "INFO-000":
        raise RuntimeError(f"경기데이터드림 API 오류: {result.get('MESSAGE', result)}")

    total_count = next((h["list_total_count"] for h in head if "list_total_count" in h), 0)
    rows = next((s["row"] for s in sections if "row" in s), [])

    return {
        "total_count": total_count,
        "items": [
            {
                "sigun_nm": row.get("SIGUN_NM"),
                "potogrf_yy": row.get("POTOGRF_YY"),
                "potogrf_div_nm": row.get("POTOGRF_DIV_NM"),
                "work_nm": row.get("WORK_NM"),
                "potogrf_plc_nm": row.get("POTOGRF_PLC_NM"),
            }
            for row in rows
        ],
    }
