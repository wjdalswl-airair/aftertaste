"""Firebase Storage에 올라간 파일을 지우는 기능 (issue #66).

리뷰 사진을 수정하거나 리뷰를 지워도 DB 행만 지워지고 Storage에 올라간 실제
파일은 안 지워지면, 아무도 참조하지 않는 파일이 계속 쌓여 저장 용량 비용이
늘어난다. 이 모듈은 그 실제 파일을 지운다.
"""

import logging
import urllib.parse

from firebase_admin import storage as firebase_storage
from google.cloud.exceptions import NotFound

from accounts.firebase import _get_firebase_app

logger = logging.getLogger(__name__)


def _object_path_from_url(photo_url):
    """Storage 다운로드 URL에서 실제 파일 경로를 꺼낸다.

    다운로드 URL은 .../o/{경로를 URL 인코딩한 값}?alt=media&token=... 형태다.
    "/o/" 다음부터 "?" 전까지를 꺼내 디코딩하면 실제 경로
    (예: reviews/{uid}/{timestamp}-{filename})가 나온다. 형태가 다르면 None.
    """
    marker = "/o/"
    start = photo_url.find(marker)
    if start == -1:
        return None
    start += len(marker)
    end = photo_url.find("?", start)
    encoded_path = photo_url[start:end] if end != -1 else photo_url[start:]
    return urllib.parse.unquote(encoded_path) or None


def delete_photo_from_storage(photo_url):
    """Firebase Storage에서 사진 파일 하나를 지운다.

    실패해도(경로를 못 읽음, 이미 없음, 권한 오류, 통신 오류 등) 예외를 올리지
    않고 로그만 남긴다 — 리뷰 CRUD 자체가 이것 때문에 막히면 안 된다
    (accounts.firebase.delete_firebase_user와 같은 best-effort 패턴).

    반환: 지웠거나 이미 없으면 True, 실패했으면 False.
    """
    object_path = _object_path_from_url(photo_url)
    if object_path is None:
        logger.warning("Storage 파일 경로를 읽을 수 없음 (photo_url=%s)", photo_url)
        return False
    try:
        app = _get_firebase_app()
        bucket = firebase_storage.bucket(app=app)
        bucket.blob(object_path).delete()
        return True
    except NotFound:
        return True  # 이미 없음 = 목표는 달성됨
    except Exception:
        logger.warning("Storage 파일 삭제 실패 (photo_url=%s)", photo_url, exc_info=True)
        return False
