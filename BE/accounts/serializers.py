from rest_framework import serializers

from accounts.models import Member


class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = [
            "id",
            "email",
            "nickname",
            "profile_image_url",
            "provider",
            "nationality",
            "language",
            "created_at",
        ]
        read_only_fields = fields


class MemberUpdateSerializer(serializers.ModelSerializer):
    """국적·언어 값을 검증할 때 쓰는 serializer (PATCH /account/locale/).

    로그인한 사용자면 이 serializer로 Member를 실제로 저장하고, 로그인하지
    않은 사용자면 값 검증에만 쓰인다(저장할 회원이 없음).

    국적→언어 자동 매핑은 하지 않는다. 프론트엔드가 보내주는 값을 그대로 저장한다.
    """

    class Meta:
        model = Member
        fields = ["nationality", "language"]


class LocaleResponseSerializer(serializers.Serializer):
    """PATCH /account/locale/ 응답 형식."""

    language = serializers.CharField(allow_null=True, required=False)


class LoginRequestSerializer(serializers.Serializer):
    """로그인 요청 body. 처음 오는 사람일 때만 agree_terms가 확인된다."""

    agree_terms = serializers.BooleanField(
        required=False,
        help_text="신규 회원가입일 때만 필요하다. true가 아니면 400을 반환한다.",
    )


class ErrorDetailSerializer(serializers.Serializer):
    """에러 응답 공통 형식."""

    detail = serializers.CharField()
