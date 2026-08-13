from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from accounts.firebase import InvalidFirebaseToken, verify_id_token
from accounts.models import Member


def _extract_bearer_token(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer "):].strip()


class FirebaseAuthentication(BaseAuthentication):
    """Firebase ID 토큰을 매 요청마다 검증하는 DRF 인증 클래스.

    회원을 새로 만들지는 않는다 (그건 로그인 API만의 책임). 여기서는 이미 있는
    회원을 찾아서 request.user에 넣어주는 일만 한다.
    """

    def authenticate(self, request):
        token = _extract_bearer_token(request)
        if not token:
            return None

        try:
            decoded_token = verify_id_token(token)
        except InvalidFirebaseToken:
            raise AuthenticationFailed("다시 로그인하세요")

        firebase_uid = decoded_token["uid"]
        try:
            member = Member.objects.get(firebase_uid=firebase_uid)
        except Member.DoesNotExist:
            return None

        return (member, decoded_token)

    def authenticate_header(self, request):
        return "Bearer"
