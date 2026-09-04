"""카카오 로그인 access token으로 사용자 정보를 확인한다.

Firebase는 카카오를 기본 로그인 제공자로 지원하지 않는다. 그래서 프론트엔드가 카카오
SDK로 로그인해 받은 access token을 서버로 보내면, 서버가 이 모듈로 카카오 API에 물어
"이 토큰이 실제로 유효하고 이 사람 것이 맞다"를 확인한다 (accounts/views.py의
KakaoCustomTokenView). 확인 뒤 Firebase 커스텀 토큰을 만드는 건 accounts/firebase.py의
create_custom_token이 한다.
"""

import requests

_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
_TIMEOUT_SECONDS = 10


class InvalidKakaoToken(Exception):
    pass


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
