from django.db import transaction
from rest_framework import serializers

from config.constants import PHOTO_URL_MAX_LENGTH
from reviews.models import REVIEW_MAX_PHOTOS, Review, ReviewPhoto


class ReviewReportSerializer(serializers.Serializer):
    """리뷰 신고 요청 body. 신고 사유는 선택 입력이다."""

    reason = serializers.CharField(required=False, allow_blank=True)


class ReviewPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewPhoto
        fields = ["id", "photo_url"]
        read_only_fields = fields


class ReviewSerializer(serializers.ModelSerializer):
    """리뷰 하나를 보여줄 때 쓰는 읽기 전용 표현 (목록·상세·전체 피드 공통)."""

    author_nickname = serializers.SerializerMethodField()
    author_profile_image_url = serializers.SerializerMethodField()
    place_name = serializers.CharField(source="place.name", read_only=True)
    place_photo_url = serializers.CharField(source="place.photo_url", read_only=True)
    photos = ReviewPhotoSerializer(many=True, read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "place",
            "place_name",
            "place_photo_url",
            "author_nickname",
            "author_profile_image_url",
            "rating",
            "content",
            "language",
            "photos",
            "like_count",
            "is_liked_by_me",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_author_nickname(self, obj):
        # 탈퇴한 사람이 쓴 리뷰는 작성자 자리에 "탈퇴한 사용자"로 보인다 (DETAIL_SPEC 3-5).
        return "탈퇴한 사용자" if obj.member.is_withdrawn else obj.member.nickname

    def get_author_profile_image_url(self, obj):
        # author_nickname과 같은 이유로, 탈퇴한 사람의 프로필 사진은 보여주지 않는다.
        if obj.member.is_withdrawn:
            return None
        return obj.member.profile_image_url or None

    def get_like_count(self, obj):
        # GET /api/reviews/(전체 피드)는 annotate(annotated_like_count=Count("likes"))로 미리
        # 센 값을 그대로 쓴다 — 명소마다 흩어진 리뷰를 한 번에 모으는 쿼리라 매번 obj.likes.count()를
        # 부르면 N+1이 커진다. 그 외(명소별 목록·내 리뷰)는 지금처럼 그때그때 센다(DETAIL_SPEC 6-1 #32).
        annotated = getattr(obj, "annotated_like_count", None)
        return annotated if annotated is not None else obj.likes.count()

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(member=request.user).exists()


class ReviewListResponseSerializer(serializers.Serializer):
    """리뷰 목록 응답 형태. 배열을 그대로 주지 않고 reviews 키로 감싼다
    (main 앱의 *ResponseSerializer, places의 SearchResponseSerializer와 같은 방식).
    실제 뷰 응답 모양과 Swagger 문서를 일치시키기 위한 것이다."""

    reviews = ReviewSerializer(many=True)


class ReviewFeedResponseSerializer(serializers.Serializer):
    """GET /api/reviews/(전체 명소 리뷰 피드) 응답 형태. 명소·내 리뷰 목록과 달리 페이지네이션이 있다."""

    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    reviews = ReviewSerializer(many=True)


class ReviewWriteSerializer(serializers.ModelSerializer):
    """리뷰 쓰기·고치기에 쓰는 시리얼라이저. photo_urls로 사진 URL 목록을 받는다.

    글자 수 제한(500자)은 Review.content의 max_length를 통해 자동으로 검증된다
    (모델 max_length와 저장 전 검증이 어긋나지 않도록, DB에 넣기 전 여기서 막는다).
    """

    # child에 max_length를 걸어 너무 긴 URL은 400으로 막는다 — 안 걸면 bulk_create가
    # 모델 검증을 건너뛰어 DB에서 "value too long"으로 500이 난다 (ReviewPhoto.photo_url 주석 참고).
    photo_urls = serializers.ListField(
        child=serializers.URLField(max_length=PHOTO_URL_MAX_LENGTH),
        required=False,
        allow_empty=True,
        write_only=True,
    )

    class Meta:
        model = Review
        fields = ["rating", "content", "language", "photo_urls"]

    def validate_photo_urls(self, value):
        if len(value) > REVIEW_MAX_PHOTOS:
            raise serializers.ValidationError(f"사진은 최대 {REVIEW_MAX_PHOTOS}장까지 등록할 수 있습니다")
        return value

    def create(self, validated_data):
        photo_urls = validated_data.pop("photo_urls", [])
        with transaction.atomic():
            review = Review.objects.create(**validated_data)
            ReviewPhoto.objects.bulk_create(
                [ReviewPhoto(review=review, photo_url=url) for url in photo_urls]
            )
        return review

    def update(self, instance, validated_data):
        photo_urls = validated_data.pop("photo_urls", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if photo_urls is not None:
            instance.photos.all().delete()
            ReviewPhoto.objects.bulk_create(
                [ReviewPhoto(review=instance, photo_url=url) for url in photo_urls]
            )
        return instance
