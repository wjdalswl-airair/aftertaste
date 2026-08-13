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


class LoginRequestSerializer(serializers.Serializer):
    """로그인 요청 body. 처음 오는 사람일 때만 agree_terms가 확인된다."""

    agree_terms = serializers.BooleanField(
        required=False,
        help_text="신규 회원가입일 때만 필요하다. true가 아니면 400을 반환한다.",
    )


class ErrorDetailSerializer(serializers.Serializer):
    """에러 응답 공통 형식."""

    detail = serializers.CharField()
