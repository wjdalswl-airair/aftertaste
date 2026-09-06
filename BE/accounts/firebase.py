import logging
import os

import firebase_admin
from django.conf import settings
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

logger = logging.getLogger(__name__)

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


def delete_firebase_user(uid):
    """Firebase Authentication에서 이 uid의 계정을 지운다 (회원 탈퇴 정리, issue #17).

    실패해도(이미 없음, 서비스 계정 키 없음, 통신 오류 등) 예외를 올리지 않고 로그만
    남긴다 — 탈퇴의 본체(DB 개인정보 익명화)는 어차피 진행돼야 하기 때문이다.

    반환: 지웠거나 이미 없으면 True, 실패했으면 False.
    """
    try:
        app = _get_firebase_app()
        firebase_auth.delete_user(uid, app=app)
        return True
    except firebase_auth.UserNotFoundError:
        return True  # 이미 없음 = 목표는 달성됨
    except Exception:
        logger.warning("Firebase 계정 삭제 실패 (uid=%s)", uid, exc_info=True)
        return False
