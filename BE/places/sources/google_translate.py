"""Google Cloud Translation API (v2) 연동 — 한국어 텍스트를 다른 언어로 옮긴다.

번역이 "제대로 됐는지" 판단하는 규칙(빈 값, 원문과 동일, 길이 비율 등)은 이 모듈이 아니라
places/translation.py에서 다룬다. 여기서는 API를 그대로 호출해서 결과 문자열만 돌려주고,
실패하면 예외를 그대로 올린다.
"""

import requests
from django.conf import settings

_TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"


def translate_text(text, target_language, source_language="ko", timeout=30):
    """text를 source_language에서 target_language로 번역한 문자열을 돌려준다.

    API 키가 없거나, 응답이 실패(4xx/5xx)이거나, timeout 안에 안 오면 예외를 그대로 올린다.
    """
    api_key = settings.GOOGLE_TRANSLATE_API_KEY
    if not api_key:
        raise RuntimeError("GOOGLE_TRANSLATE_API_KEY가 설정되지 않았습니다 (.env 확인).")

    params = {"key": api_key}
    payload = {"q": text, "target": target_language, "source": source_language, "format": "text"}

    response = requests.post(_TRANSLATE_URL, params=params, data=payload, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    return data["data"]["translations"][0]["translatedText"]
