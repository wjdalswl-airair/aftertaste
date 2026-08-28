from rest_framework import serializers

from accounts.models import Member
from courses.models import Course
from reviews.models import Review


class MemberSerializer(serializers.ModelSerializer):
    # 마이페이지 프로필 상단 활동 요약 (docs/DETAIL_SPEC.md 3-1, 6-1 #22).
    # - reviewed_places_count: 내가 리뷰를 쓴 서로 다른 명소 수 ("방문 인증한 촬영지").
    #   실제 방문 인증 기능이 아니라 리뷰 수를 명소 단위로 센 것뿐이다. 관리자가 감춘
    #   리뷰는 뺀다. (삭제한 리뷰는 물리적으로 지워져 자연히 빠진다.)
    # - created_courses_count: 내가 만든 코스 수 ("제안한 코스").
    reviewed_places_count = serializers.SerializerMethodField()
    created_courses_count = serializers.SerializerMethodField()

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
            "reviewed_places_count",
            "created_courses_count",
        ]
        read_only_fields = fields

    def get_reviewed_places_count(self, obj):
        return (
            Review.objects.filter(member=obj, is_hidden=False)
            .values("place")
            .distinct()
            .count()
        )

    def get_created_courses_count(self, obj):
        return Course.objects.filter(creator=obj).count()


class MemberUpdateSerializer(serializers.ModelSerializer):
    """국적·언어 값을 검증할 때 쓰는 serializer (PATCH /account/locale/).

    로그인한 사용자면 이 serializer로 Member를 실제로 저장하고, 로그인하지
    않은 사용자면 값 검증에만 쓰인다(저장할 회원이 없음).

    국적→언어 자동 매핑은 하지 않는다. 프론트엔드가 보내주는 값을 그대로 저장한다.
    """

    class Meta:
        model = Member
        fields = ["nationality", "language"]


class MemberProfileUpdateSerializer(serializers.ModelSerializer):
    """프로필(닉네임) 수정에 쓰는 serializer (PATCH /account/).

    로그인한 본인만 호출할 수 있다(뷰에서 IsAuthenticated로 막음). 닉네임 길이
    제한(20자, docs/DETAIL_SPEC.md 6-1 #21)은 ModelSerializer가 Member.nickname의
    max_length를 그대로 가져와 자동으로 검증해준다 - 넘는 값을 보내면 저장 전에
    400으로 막힌다.
    """

    class Meta:
        model = Member
        fields = ["nickname"]


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
