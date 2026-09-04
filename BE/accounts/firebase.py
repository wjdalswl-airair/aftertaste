import os

import firebase_admin
from django.conf import settings
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

_firebase_app = None


class InvalidFirebaseToken(Exception):
    pass


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            raise InvalidFirebaseToken(
                "Firebase 서비스 계정 키가 설정되지 않았습니다."
            )
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def verify_id_token(token):
    """Firebase ID 토큰을 검증하고 decoded token(dict)을 반환한다.

    토큰이 없거나 잘못됐거나 만료됐으면 InvalidFirebaseToken을 던진다.
    """
    app = _get_firebase_app()
    try:
        return firebase_auth.verify_id_token(token, app=app)
    except Exception as exc:
        raise InvalidFirebaseToken(str(exc)) from exc


def create_custom_token(uid, claims=None):
    """이 uid로 Firebase 커스텀 토큰을 만든다.

    Firebase가 기본으로 지원하지 않는 로그인 방식(카카오)을 위한 것이다. 서버가
    다른 방법으로 "이 사람이 맞다"를 확인한 뒤 이 함수로 토큰을 만들어 클라이언트에
    주면, 클라이언트는 signInWithCustomToken으로 Firebase에 로그인한다. claims에
    넣은 값(email/name/picture 등)은 이후 발급되는 Firebase ID 토큰에 그대로
    실려서, 기존 LoginView가 소셜 로그인 때와 같은 방식으로 읽어갈 수 있다.
    """
    app = _get_firebase_app()
    token_bytes = firebase_auth.create_custom_token(uid, developer_claims=claims, app=app)
    return token_bytes.decode("utf-8")
