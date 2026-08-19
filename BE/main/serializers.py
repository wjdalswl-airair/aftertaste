from rest_framework import serializers

from main.models import Banner


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ["id", "image_url", "link_url", "order"]
        read_only_fields = fields


class BannerListResponseSerializer(serializers.Serializer):
    """GET /api/banners/ 응답 형태. API 명세서가 다른 엔드포인트와 같은 방식으로
    응답을 키로 감싸므로(예: { spots[] }), 배너도 배열을 그대로 주지 않고
    banners 키로 감싼다."""

    banners = BannerSerializer(many=True)
