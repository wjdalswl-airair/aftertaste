from rest_framework import serializers

from main.models import Banner
from places.models import Place
from reviews.serializers import ReviewSerializer


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


class HallOfFameResponseSerializer(serializers.Serializer):
    """GET /api/main/hall-of-fame/ 응답 형태 (PHASES/PHASE3.md 6번).

    이번 주 좋아요가 가장 많은, 사진이 있는 리뷰 하나를 review에 담아 돌려준다.
    후보가 하나도 없으면(이번 주 좋아요 데이터가 없음) review는 null이다 —
    화면이 깨지면 안 되므로 오류로 처리하지 않는다.
    """

    review = ReviewSerializer(allow_null=True)


class TopPlaceSerializer(serializers.ModelSerializer):
    """Top10 캐러셀에 보여줄 명소 정보. favorite_count는 뷰의 annotate로 채워진다.

    is_favorited는 "지금 로그인한 사람이 이 명소를 이미 즐겨찾기 했는지"다. 뷰가
    context["favorited_place_ids"]에 그 사람의 즐겨찾기 place_id 집합을 넣어줘야 하고,
    안 넣으면 항상 False다 (PlaceSearchSerializer.is_favorited와 같은 규칙, fix/be/main-tab-favorite).
    """

    favorite_count = serializers.IntegerField(read_only=True)
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ["id", "name", "address", "photo_url", "favorite_count", "is_favorited"]
        read_only_fields = fields

    def get_is_favorited(self, obj):
        return obj.id in self.context.get("favorited_place_ids", set())


class TopPlaceListResponseSerializer(serializers.Serializer):
    """GET /api/main/top-places/ 응답 형태."""

    places = TopPlaceSerializer(many=True)
