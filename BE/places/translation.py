"""명소·작품 번역을 처리하는 서비스 계층 (DETAIL_SPEC 4장, PHASES/PHASE4.md 4-3).

여기서 하는 일 세 가지:
1. 명소/작품 하나를 실제로 번역해서 PlaceTranslation/WorkTranslation에 저장한다.
   (실패 판정 규칙, 30초 제한, 실패해도 예외를 올리지 않고 상태만 남기는 것 포함)
2. "지금 보여줄 언어"를 정한다 (쿼리파라미터 lang → 로그인 회원 언어 → 한국어).
3. 명소/작품 인스턴스에서 그 언어의 승인된 번역이 있으면 그 값을, 없으면 원문을 고른다.
"""

import logging

from django.utils import timezone

from places.models import PlaceTranslation, TranslationStatus, WorkTranslation
from places.sources import google_translate

logger = logging.getLogger(__name__)

# 명소·작품은 관리자가 미리 하는 일이라 아무도 기다리지 않는다 (DETAIL_SPEC 4-3, 리뷰의 5초와 다름).
PLACE_WORK_TRANSLATE_TIMEOUT_SECONDS = 30

# name/title은 CharField(max_length=200)이라 이 길이를 넘으면 DB 저장이 실패한다.
# 번역 결과가 이보다 길면 잘라서 저장한다 (SearchHistory.keyword 초과 때와 같은 처리 방식).
NAME_TITLE_MAX_LENGTH = 200
CHARFIELD_TRUNCATE_FIELDS = {"name", "title"}

# 길이 검사는 원문이 이 글자수를 넘을 때만 적용한다. 그래야 "청계천"(3자) → "Cheonggyecheon"(14자,
# 4.7배)같은 정상적인 짧은 음역이 실패로 오해받지 않는다 (DETAIL_SPEC 4-3).
LENGTH_CHECK_MIN_SOURCE_LENGTH = 20
LENGTH_RATIO_MIN = 1 / 5
LENGTH_RATIO_MAX = 5

# 지원 언어 목록. 지금은 영어만이지만(DETAIL_SPEC 6-1 #14), 이후 언어가 늘어날 걸 감안해 목록으로 둔다.
SUPPORTED_LANGUAGES = ["en"]


def _translate_one(text, target_language):
    """텍스트 하나를 번역해서 (번역문, 성공여부)를 돌려준다.

    원문이 비어 있으면 번역할 게 없으니 성공으로 치고 빈 문자열을 돌려준다.
    확실한 실패 규칙(DETAIL_SPEC 4-3 (1))에 걸리면 (None, False)를 돌려준다.
    """
    if not text:
        return "", True

    try:
        translated = google_translate.translate_text(
            text, target_language, timeout=PLACE_WORK_TRANSLATE_TIMEOUT_SECONDS
        )
    except Exception:
        # 답이 안 옴 / 시간 초과 / 그 외 통신 오류
        logger.warning("번역 요청 실패 (text=%r, target=%s)", text[:30], target_language, exc_info=True)
        return None, False

    if not translated:
        return None, False
    if translated == text:
        return None, False
    if len(text) > LENGTH_CHECK_MIN_SOURCE_LENGTH:
        ratio = len(translated) / len(text)
        if ratio < LENGTH_RATIO_MIN or ratio > LENGTH_RATIO_MAX:
            return None, False

    return translated, True


def _apply_translation(translation, field_results):
    """번역 결과를 translation 레코드에 반영한다.

    field_results: [(필드이름, 번역문 또는 None, 성공여부), ...]
    실패한 필드는 기존 값을 그대로 둔다 (부분 성공을 지우지 않기 위해).
    실제로 내용이 바뀐 필드가 하나라도 있으면(=하나라도 성공하면) 재승인이 필요해서
    is_approved를 False로 되돌린다 (DETAIL_SPEC 4-3 (2): 자동 번역은 관리자가 다시
    확인해야 손님에게 보인다). 반대로 전부 실패해서 내용이 하나도 안 바뀌었다면,
    이미 승인되어 노출 중이던 번역을 건드리지 않고 is_approved를 그대로 둔다.
    (일시적인 API 실패 한 번 때문에 정상 노출 중이던 번역이 사라지면 안 된다.)
    """
    all_ok = True
    any_changed = False
    for field_name, value, ok in field_results:
        if ok:
            # name/title은 CharField(200)이라 넘치면 DB가 예외를 던진다. 잘라서 저장한다.
            if field_name in CHARFIELD_TRUNCATE_FIELDS and value and len(value) > NAME_TITLE_MAX_LENGTH:
                value = value[:NAME_TITLE_MAX_LENGTH]
            setattr(translation, field_name, value)
            any_changed = True
        else:
            all_ok = False

    if any_changed:
        translation.is_approved = False
    if all_ok:
        translation.status = TranslationStatus.SUCCESS
        translation.translated_at = timezone.now()
    else:
        translation.status = TranslationStatus.FAILED
    translation.save()
    return translation


def translate_place(place, language="en"):
    """명소 하나를 language로 번역해서 PlaceTranslation에 저장한다. 실패해도 예외를 올리지 않는다."""
    translation, _ = PlaceTranslation.objects.get_or_create(place=place, language=language)

    name, name_ok = _translate_one(place.name, language)
    description, description_ok = _translate_one(place.description, language)

    return _apply_translation(
        translation, [("name", name, name_ok), ("description", description, description_ok)]
    )


def translate_work(work, language="en"):
    """작품 하나를 language로 번역해서 WorkTranslation에 저장한다. 실패해도 예외를 올리지 않는다."""
    translation, _ = WorkTranslation.objects.get_or_create(work=work, language=language)

    title, title_ok = _translate_one(work.title, language)
    description, description_ok = _translate_one(work.description, language)

    return _apply_translation(
        translation, [("title", title, title_ok), ("description", description, description_ok)]
    )


def translate_place_all_languages(place):
    for language in SUPPORTED_LANGUAGES:
        translate_place(place, language)


def translate_work_all_languages(work):
    for language in SUPPORTED_LANGUAGES:
        translate_work(work, language)


def resolve_language(request):
    """응답 언어를 정한다: 쿼리파라미터 lang → 로그인 회원의 언어 → None(한국어 원문).

    (DETAIL_SPEC 6-1 - 명소·작품 정보를 어느 언어로 보여줄지 결정 순서)
    """
    lang = (request.query_params.get("lang") or "").strip()
    if lang:
        return lang
    if request.user.is_authenticated and request.user.language:
        return request.user.language
    return None


def pick_translated_text(instance, field, language):
    """instance(Place/Work)의 field를 language로 보여줄 값으로 고른다.

    같은 언어 + 승인된(is_approved=True) 번역이 있으면 그 값을, 없으면 원문을 돌려준다.
    instance.translations가 미리 prefetch 되어 있다는 전제로 짜여 있어서(N+1 방지),
    추가 쿼리 없이 메모리에서만 고른다.
    """
    original = getattr(instance, field)
    if not language:
        return original
    for translation in instance.translations.all():
        if translation.language == language and translation.is_approved:
            value = getattr(translation, field, "")
            return value if value else original
    return original
