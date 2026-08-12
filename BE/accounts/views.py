from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import FirebaseAuthentication, _extract_bearer_token
from accounts.firebase import InvalidFirebaseToken, verify_id_token
from accounts.models import Member
from accounts.serializers import (
    ErrorDetailSerializer,
    LoginRequestSerializer,
    MemberSerializer,
)

PROVIDER_BY_SIGN_IN_PROVIDER = {
    "google.com": Member.Provider.GOOGLE,
    "apple.com": Member.Provider.APPLE,
}


class FirebaseAuthenticationScheme(OpenApiAuthenticationExtension):
    """Swagger UI에 Bearer 토큰 입력창(Authorize 버튼)을 띄우기 위한 스킴 등록."""

    target_class = FirebaseAuthentication
    name = "FirebaseAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "Firebase ID Token",
            "description": "Firebase ID 토큰. `Authorization: Bearer <token>` 형식으로 보낸다.",
        }


class LoginView(APIView):
    """Firebase ID 토큰으로 로그인한다. 처음 온 사람이면 회원을 새로 만든다."""

    @extend_schema(
        summary="소셜 로그인 / 자동 회원가입",
        description=(
            "Firebase ID 토큰(Google·Apple 로그인 결과)을 검증해서 회원을 찾거나 새로 만든다.\n\n"
            "- 이미 있는 회원이면 body 없이도 200을 반환한다.\n"
            "- 처음 오는 회원이면 body에 `agree_terms: true`가 있어야 가입이 완료된다."
        ),
        request=LoginRequestSerializer,
        responses={
            200: MemberSerializer,
            201: MemberSerializer,
            400: OpenApiResponse(
                response=ErrorDetailSerializer,
                description="약관 동의 누락 또는 지원하지 않는 로그인 방식",
            ),
            401: OpenApiResponse(
                response=ErrorDetailSerializer,
                description="토큰 없음/무효/만료",
            ),
        },
        examples=[
            OpenApiExample(
                "신규 가입 요청",
                value={"agree_terms": True},
                request_only=True,
            ),
            OpenApiExample(
                "약관 동의 필요",
                value={"detail": "약관 동의가 필요합니다"},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "지원하지 않는 로그인 방식",
                value={"detail": "지원하지 않는 로그인 방식입니다"},
                response_only=True,
                status_codes=["400"],
            ),
            OpenApiExample(
                "토큰 없음/무효/만료",
                value={"detail": "다시 로그인하세요"},
                response_only=True,
                status_codes=["401"],
            ),
        ],
    )
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

    @extend_schema(
        summary="내 정보 조회",
        description="로그인한 회원 본인의 정보를 반환한다.",
        responses={
            200: MemberSerializer,
            401: OpenApiResponse(
                response=ErrorDetailSerializer,
                description="로그인 필요",
            ),
        },
        examples=[
            OpenApiExample(
                "로그인 필요",
                value={"detail": "로그인이 필요한 기능입니다"},
                response_only=True,
                status_codes=["401"],
            ),
        ],
    )
    def get(self, request):
        return Response(MemberSerializer(request.user).data)
