from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import _extract_bearer_token
from accounts.firebase import InvalidFirebaseToken, verify_id_token
from accounts.models import Member
from accounts.serializers import MemberSerializer

PROVIDER_BY_SIGN_IN_PROVIDER = {
    "google.com": Member.Provider.GOOGLE,
    "apple.com": Member.Provider.APPLE,
}


class LoginView(APIView):
    """Firebase ID 토큰으로 로그인한다. 처음 온 사람이면 회원을 새로 만든다."""

    def post(self, request):
        token = _extract_bearer_token(request)
        if not token:
            raise AuthenticationFailed("다시 로그인하세요")

        try:
            decoded_token = verify_id_token(token)
        except InvalidFirebaseToken:
            raise AuthenticationFailed("다시 로그인하세요")

        firebase_uid = decoded_token["uid"]

        try:
            member = Member.objects.get(firebase_uid=firebase_uid)
            return Response(MemberSerializer(member).data)
        except Member.DoesNotExist:
            pass

        if request.data.get("agree_terms") is not True:
            return Response({"detail": "약관 동의가 필요합니다"}, status=400)

        sign_in_provider = decoded_token.get("firebase", {}).get("sign_in_provider")
        provider = PROVIDER_BY_SIGN_IN_PROVIDER.get(sign_in_provider)
        if provider is None:
            return Response({"detail": "지원하지 않는 로그인 방식입니다"}, status=400)

        member = Member.objects.create(
            firebase_uid=firebase_uid,
            provider=provider,
            email=decoded_token.get("email"),
            nickname=decoded_token.get("name"),
            profile_image_url=decoded_token.get("picture"),
            agreed_terms_at=timezone.now(),
        )
        return Response(MemberSerializer(member).data, status=201)


class MeView(APIView):
    """로그인한 사람만 자기 정보를 볼 수 있다."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MemberSerializer(request.user).data)
