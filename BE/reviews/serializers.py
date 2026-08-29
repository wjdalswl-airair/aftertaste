from django.db import transaction
from rest_framework import serializers

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
    """리뷰 하나를 보여줄 때 쓰는 읽기 전용 표현 (목록·상세 공통)."""

    author_nickname = serializers.SerializerMethodField()
    photos = ReviewPhotoSerializer(many=True, read_only=True)
    like_count = serializers.IntegerField(source="likes.count", read_only=True)
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id",
            "place",
            "author_nickname",
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

    def get_is_liked_by_me(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(member=request.user).exists()


class ReviewWriteSerializer(serializers.ModelSerializer):
    """리뷰 쓰기·고치기에 쓰는 시리얼라이저. photo_urls로 사진 URL 목록을 받는다.

    글자 수 제한(500자)은 Review.content의 max_length를 통해 자동으로 검증된다
    (모델 max_length와 저장 전 검증이 어긋나지 않도록, DB에 넣기 전 여기서 막는다).
    """

    photo_urls = serializers.ListField(
        child=serializers.URLField(), required=False, allow_empty=True, write_only=True
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
