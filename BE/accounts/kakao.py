"""카카오 로그인 — 인가 코드를 access token으로 바꾸고, 그 토큰으로 사용자 정보를 확인한다.

Firebase는 카카오를 기본 로그인 제공자로 지원하지 않는다. 그래서:
1. 프론트엔드가 `Kakao.Auth.authorize()`로 로그인하면 카카오가 **인가 코드(code)**만 돌려준다
   (예전 `Kakao.Auth.login()`이 주던 access token은 더 이상 안 준다).
2. 프론트엔드가 그 code와 redirect_uri를 서버로 보낸다.
3. 서버가 `exchange_code_for_token`으로 카카오 OAuth 서버에서 access token을 받고,
   `get_kakao_user`로 "이 사람이 누구인지" 확인한다 (accounts/views.py의 KakaoCustomTokenView).

access token을 프론트엔드가 직접 만지지 않게 되어 보안상 낫다.
확인 뒤 Firebase 커스텀 토큰을 만드는 건 accounts/firebase.py의 create_custom_token이 한다.
"""

import requests
from django.conf import settings

_TOKEN_URL = "https://kauth.kakao.com/oauth/token"
_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
_TIMEOUT_SECONDS = 10


class InvalidKakaoToken(Exception):
    pass


def exchange_code_for_token(code, redirect_uri):
    """카카오 인가 코드(code)를 access token으로 바꾼다.

    code가 없거나 잘못됐거나 이미 쓴 코드거나, redirect_uri가 authorize 때와 다르거나,
    카카오 서버에 문제가 있으면 InvalidKakaoToken을 던진다.

    redirect_uri는 프론트엔드가 authorize()에 넘긴 값과 **정확히 같아야** 한다 (카카오 규칙).
    """
    if not code:
        raise InvalidKakaoToken("인가 코드(code)가 없습니다.")
    if not settings.KAKAO_API_KEY:
        raise InvalidKakaoToken("KAKAO_API_KEY가 설정되지 않았습니다 (.env 확인).")

    data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_API_KEY,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    if settings.KAKAO_CLIENT_SECRET:
        data["client_secret"] = settings.KAKAO_CLIENT_SECRET

    try:
        response = requests.post(_TOKEN_URL, data=data, timeout=_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise InvalidKakaoToken(str(exc)) from exc

    if response.status_code != 200:
        # 카카오는 실패 시 {"error": "...", "error_description": "..."}를 준다.
        body = _safe_json(response)
        raise InvalidKakaoToken(
            f"카카오 토큰 교환 실패: HTTP {response.status_code} {body.get('error_description') or body.get('error') or ''}"
        )

    access_token = _safe_json(response).get("access_token")
    if not access_token:
        raise InvalidKakaoToken("카카오 응답에 access_token이 없습니다.")
    return access_token


def _safe_json(response):
    try:
        return response.json()
    except ValueError:
        return {}


def get_kakao_user(access_token):
    """카카오 access token으로 사용자 정보를 가져온다.

    토큰이 없거나 잘못됐거나 만료됐으면, 또는 카카오 서버에 문제가 있으면
    InvalidKakaoToken을 던진다.

    반환값: {"kakao_id", "email", "nickname", "profile_image_url"}
    이메일·닉네임·프로필사진은 사용자가 카카오 로그인 동의 화면에서 제공에
    동의하지 않았으면 없을 수 있다(None).
    """
    if not access_token:
        raise InvalidKakaoToken("access_token이 없습니다.")

    try:
        response = requests.get(
            _USER_ME_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise InvalidKakaoToken(str(exc)) from exc

    if response.status_code != 200:
        raise InvalidKakaoToken(f"카카오 사용자 조회 실패: HTTP {response.status_code}")

    data = response.json()
    kakao_id = data.get("id")
    if not kakao_id:
        raise InvalidKakaoToken("카카오 응답에 사용자 id가 없습니다.")

    account = data.get("kakao_account") or {}
    profile = account.get("profile") or {}

    return {
        "kakao_id": kakao_id,
        "email": account.get("email"),
        "nickname": profile.get("nickname"),
        "profile_image_url": profile.get("profile_image_url"),
    }
