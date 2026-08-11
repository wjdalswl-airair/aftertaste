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
