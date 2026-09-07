"""명소 한 곳을 기준으로, 카카오 주변 상권 후보 중에서 Claude가 코스를 골라 만든다.

Claude가 하는 일은 딱 세 가지다:
  (1) 후보 목록 중에서 식당 1곳·카페 1곳·그 외 1곳을 고른다,
  (2) 명소 다음의 방문 순서를 정한다,
  (3) 코스 제목과 한 줄 소개를 쓴다.

예상 소요시간·이동거리 같은 숫자는 만들지 않는다 — 모델이 그럴듯하게 지어내기 쉬운 값이라,
필요해지면 카카오 길찾기 API로 따로 뽑는다. 지금 응답 형태(Course)에도 그런 필드는 없다.

카카오 후보 조회는 places.views._fetch_nearby_places를 그대로 재사용하고, "어떤 결과가
어떤 role(식당/카페/그 외)인지"는 프론트(getCoursePlaceRole)와 같은 기준(카테고리 문자열
키워드)을 쓴다.
"""

import logging

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

# 코스 한 개에 꼭 있어야 하는 세 자리 (CoursePlace.Role과 같은 값).
_ROLES = ("RESTAURANT", "CAFE", "OTHER")

_SYSTEM_PROMPT = (
    "너는 영화·드라마 촬영지 여행 코스를 짜 주는 도우미다. "
    "사용자가 고른 촬영 명소 한 곳과 그 주변 가게·장소 후보 목록을 준다. "
    "후보 중에서 식당 1곳, 카페 1곳, 그 외 장소 1곳을 골라 "
    "그 명소에서 출발하는 반나절 코스를 만들어라. "
    "반드시 후보 목록에 있는 장소만, 그 ref 번호로 고른다. "
    "코스 제목은 촬영 명소의 분위기를 담아 12자 이내로, "
    "한 줄 소개는 이 코스의 매력을 25자 이내 한국어로 쓴다. "
    "submit_course 도구로만 답한다."
)

# Claude가 이 스키마에 맞춰 답하도록 강제한다 (tool_choice로 이 도구를 반드시 쓰게 함).
_TOOL = {
    "name": "submit_course",
    "description": "고른 코스를 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "코스 제목 (12자 이내)"},
            "description": {"type": "string", "description": "한 줄 소개 (25자 이내)"},
            "restaurant_ref": {"type": "integer", "description": "고른 식당 후보의 ref 번호"},
            "cafe_ref": {"type": "integer", "description": "고른 카페 후보의 ref 번호"},
            "other_ref": {"type": "integer", "description": "고른 그 외 장소 후보의 ref 번호"},
            "visit_order": {
                "type": "array",
                "items": {"type": "string", "enum": list(_ROLES)},
                "description": "명소 다음의 방문 순서. RESTAURANT/CAFE/OTHER를 한 번씩.",
            },
        },
        "required": [
            "title",
            "description",
            "restaurant_ref",
            "cafe_ref",
            "other_ref",
            "visit_order",
        ],
    },
}


class CourseAiError(Exception):
    """AI 코스 생성이 실패했다.

    reason:
      "no_candidates"  - 주변에 식당/카페/그 외 후보가 부족하다 (뷰에서 422로 응답)
      그 외            - 키 미설정 / Claude 호출 실패 / 응답이 이상함 (뷰에서 503으로 응답)
    """

    def __init__(self, message, *, reason):
        super().__init__(message)
        self.reason = reason


def role_of(category_name):
    """카카오 카테고리 문자열을 코스 role로 바꾼다 (FE getCoursePlaceRole과 같은 기준)."""
    name = category_name or ""
    if "카페" in name:
        return "CAFE"
    if "음식점" in name:
        return "RESTAURANT"
    return "OTHER"


def _bucket_candidates(nearby_places):
    """후보에 ref 번호(0,1,2,...)를 매기고 role별로 나눈다.

    돌려주는 값: (by_ref={ref: 후보 dict}, by_role={role: [ref, ...]}).
    """
    by_ref = {}
    by_role = {role: [] for role in _ROLES}
    for ref, item in enumerate(nearby_places):
        by_ref[ref] = item
        by_role[role_of(item.get("category_name"))].append(ref)
    return by_ref, by_role


def _format_candidates(by_ref):
    """후보 목록을 Claude에게 보여줄 텍스트로 만든다."""
    lines = []
    for ref, item in by_ref.items():
        lines.append(
            f"- ref {ref}: {item.get('place_name')} "
            f"[{role_of(item.get('category_name'))}] "
            f"({item.get('category_name') or '분류 없음'}) / "
            f"{item.get('address_name') or '주소 없음'}"
        )
    return "\n".join(lines)


def _extract_tool_input(response):
    """Claude 응답에서 submit_course 도구 입력(dict)을 꺼낸다."""
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_course":
            return block.input
    raise CourseAiError("AI 응답에서 코스를 찾지 못했습니다.", reason="bad_response")


def _build_result(payload, place, by_ref, by_role):
    """Claude가 준 값을 검증해서, Course/CoursePlace를 만들 dict로 바꾼다.

    모델이 목록 밖 후보를 고르거나 role을 헷갈리면, 그 role의 첫 번째 후보로 조용히 대체한다
    (사용자에게 오류를 던지기보다 그럴듯한 코스를 주는 편이 낫다).
    """
    ref_by_role = {
        "RESTAURANT": payload.get("restaurant_ref"),
        "CAFE": payload.get("cafe_ref"),
        "OTHER": payload.get("other_ref"),
    }
    chosen = {}
    for role, ref in ref_by_role.items():
        if ref not in by_ref or ref not in by_role[role]:
            ref = by_role[role][0]
        chosen[role] = by_ref[ref]

    order = payload.get("visit_order") or []
    if sorted(order) != sorted(_ROLES):
        order = list(_ROLES)

    places = []
    for position, role in enumerate(order):
        item = chosen[role]
        places.append(
            {
                "role": role,
                "order": position,
                "name": item.get("place_name") or "",
                "address": item.get("address_name") or "",
                "road_address_name": item.get("road_address_name") or "",
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "category_name": item.get("category_name") or "",
                "kakao_place_id": item.get("id"),
            }
        )

    title = (payload.get("title") or "").strip()[:200] or f"{place.name} 코스"
    description = (payload.get("description") or "").strip()
    return {"title": title, "description": description, "places": places}


def recommend_course(place, nearby_places):
    """place를 기준으로 nearby_places 중에서 코스를 골라 만든다.

    돌려주는 값: {"title": str, "description": str, "places": [CoursePlace 만들 dict, ...]}.
    실패하면 CourseAiError를 던진다.
    """
    by_ref, by_role = _bucket_candidates(nearby_places)
    missing = [role for role in _ROLES if not by_role[role]]
    if missing:
        raise CourseAiError(
            "주변에서 코스에 넣을 후보(식당·카페·그 외)를 충분히 찾지 못했습니다.",
            reason="no_candidates",
        )

    if not settings.ANTHROPIC_API_KEY:
        raise CourseAiError("ANTHROPIC_API_KEY가 설정되지 않았습니다.", reason="not_configured")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    user_text = (
        f"촬영 명소: {place.name} ({place.address or '주소 없음'})\n\n"
        f"주변 후보 목록:\n{_format_candidates(by_ref)}"
    )
    try:
        response = client.messages.create(
            model=settings.COURSE_AI_MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_text}],
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "submit_course"},
        )
    except anthropic.AnthropicError as exc:
        logger.warning("AI 코스 추천 - Claude 호출 실패 (place_id=%s): %s", place.id, exc)
        raise CourseAiError(
            "AI 코스 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.", reason="api_error"
        ) from exc

    payload = _extract_tool_input(response)
    return _build_result(payload, place, by_ref, by_role)
