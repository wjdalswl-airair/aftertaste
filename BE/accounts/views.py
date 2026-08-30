import uuid

from django.utils import timezone
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import FirebaseAuthentication, _extract_bearer_token
from accounts.firebase import InvalidFirebaseToken, verify_id_token
from accounts.models import NICKNAME_MAX_LENGTH, Member
from accounts.serializers import (
    ErrorDetailSerializer,
    LocaleResponseSerializer,
    LoginRequestSerializer,
    MemberProfileUpdateSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
)

# Firebase ID 토큰의 firebase.sign_in_provider 문자열 → Member.Provider.
# 카카오는 Firebase 기본 제공자가 아니라, 프론트가 Firebase에 OIDC 커스텀 제공자로
# 붙여서 쓴다. 그래서 sign_in_provider 값이 "oidc.<프론트가 콘솔에 등록한 providerId>"
# 형태다. 아래 "oidc.kakao"는 예상값이고, 실제 문자열은 프론트와 맞춰 확정해야 한다
# (docs/DETAIL_SPEC.md 6-1 #19).
PROVIDER_BY_SIGN_IN_PROVIDER = {
    "google.com": Member.Provider.GOOGLE,
    "oidc.kakao": Member.Provider.KAKAO,
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
            "Firebase ID 토큰(Google·Kakao 로그인 결과)을 검증해서 회원을 찾거나 새로 만든다.\n\n"
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

        # 소셜에서 받은 이름이 닉네임 최대 길이(20자)를 넘으면 잘라서 저장한다.
        # 그대로 넣으면 DB varchar 길이를 초과해 가입이 실패한다.
        social_name = decoded_token.get("name")
        nickname = social_name[:NICKNAME_MAX_LENGTH] if social_name else social_name

        member = Member.objects.create(
            firebase_uid=firebase_uid,
            provider=provider,
            email=decoded_token.get("email"),
            nickname=nickname,
            profile_image_url=decoded_token.get("picture"),
            agreed_terms_at=timezone.now(),
        )
        return Response(MemberSerializer(member).data, status=201)


class MeView(APIView):
    """로그인한 사람만 자기 정보를 보고, 고치고, 탈퇴할 수 있다."""

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

    @extend_schema(
        summary="프로필(닉네임·프로필 사진) 수정",
        description=(
            "로그인한 회원 본인의 닉네임과 프로필 사진 URL을 바꾼다. 둘 다 선택 항목이라 "
            "보낸 값만 반영된다. 프로필 사진 파일은 서버가 받지 않는다 — 프론트엔드가 "
            "Firebase Storage에 올린 URL을 보내고, 빈 값이면 사진을 지운다."
        ),
        request=MemberProfileUpdateSerializer,
        responses={
            200: None,
            400: OpenApiResponse(response=ErrorDetailSerializer, description="닉네임 길이 초과 또는 사진 URL 형식 오류"),
            401: OpenApiResponse(response=ErrorDetailSerializer, description="로그인 필요"),
        },
    )
    def patch(self, request):
        serializer = MemberProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=200)

    @extend_schema(
        summary="회원 탈퇴",
        description=(
            "회원 row는 지우지 않는다(리뷰·즐겨찾기가 주인을 잃지 않도록). 대신 닉네임·이메일·"
            "프로필사진 같은 개인정보만 비우고 `is_withdrawn=True`로 표시한다. 탈퇴 후에는 "
            "같은 소셜 계정으로 다시 로그인해도 이 회원이 아니라 새 회원으로 시작된다."
        ),
        request=None,
        responses={
            204: None,
            401: OpenApiResponse(response=ErrorDetailSerializer, description="로그인 필요"),
        },
    )
    def delete(self, request):
        member = request.user
        member.nickname = None
        member.email = None
        member.profile_image_url = None
        # firebase_uid를 다른 값으로 바꿔서(익명화) 더 이상 로그인에 쓸 수 없게 한다.
        # firebase_uid는 unique라서 원래 값 그대로 두면, 같은 사람이 다시 로그인할 때
        # LoginView가 이 탈퇴 회원을 그대로 찾아버려서 "새 회원으로 시작"이 안 된다.
        # 값을 바꿔두면 다음 로그인 때 원래 firebase_uid로는 아무도 안 찾아지므로
        # 자동으로 새 Member가 만들어진다.
        member.firebase_uid = f"withdrawn:{uuid.uuid4()}"
        member.is_withdrawn = True
        member.withdrawn_at = timezone.now()
        member.save()
        return Response(status=204)


class LocaleView(APIView):
    """국적·언어를 설정한다. 로그인 여부와 상관없이 호출할 수 있다.

    - 로그인한 사용자(Authorization 헤더에 유효한 토큰이 있으면)는 그 회원의
      국적·언어를 서버에 저장한다.
    - 로그인하지 않은 사용자는 저장할 회원이 없으므로 값만 검증하고 응답만 돌려준다.
      비로그인 사용자의 실제 보관은 프론트엔드(localStorage) 몫이다 (DETAIL_SPEC 6-1 #8).

    별도로 permission_classes를 지정하지 않는다 — 프로젝트 기본값(AllowAny)이 이미
    "로그인 없이도 호출 가능"과 맞고, FirebaseAuthentication은 토큰이 없으면 그냥
    None을 돌려줘서 request.user가 AnonymousUser가 될 뿐 에러를 내지 않는다.

    토큰이 있는데 무효/만료된 경우는 다르다 — FirebaseAuthentication이
    AuthenticationFailed(401)를 던지는데, 이 API는 로그인이 필요 없으므로 이 뷰에서는
    그 예외를 잡아 비로그인 사용자와 동일하게(값 검증만, 저장은 안 함) 처리한다.
    다른 뷰(LoginView, MeView)는 로그인이 필요한 API라 401이 그대로 맞다.

    "400 지원하지 않는 언어" 에러케이스는 아직 만들지 않았다. 지원 언어 목록이
    PRD에서 확정되면(DETAIL_SPEC 7장 #8) 그때 검증 로직을 추가해야 한다.
    """

    def perform_authentication(self, request):
        # 토큰이 무효/만료면 request.user 접근 시 AuthenticationFailed가 난다.
        # 여기서 잡아주면 request.user는 AnonymousUser로 남고, patch()가 정상 실행된다.
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="국적·언어 설정",
        description=(
            "국적·언어를 저장한다. 로그인한 사용자면 회원 정보에 저장하고, "
            "로그인하지 않았으면 값만 검증하고 응답만 돌려준다(실제 보관은 프론트엔드 책임).\n\n"
            "국적에 맞는 언어를 서버가 자동으로 정해주지는 않는다 — 프론트엔드가 보낸 값을 그대로 쓴다."
        ),
        request=MemberUpdateSerializer,
        responses={200: LocaleResponseSerializer},
    )
    def patch(self, request):
        member = request.user if request.user.is_authenticated else None
        serializer = MemberUpdateSerializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if member is not None:
            serializer.save()
        return Response({"language": serializer.validated_data.get("language")})
