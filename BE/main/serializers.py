from rest_framework import serializers

from main.models import Banner
from places.models import Place
from places.translation import pick_translated_text
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


class HallOfFamePlaceSerializer(serializers.ModelSerializer):
    """명예의전당 카드 캡션에 필요한 최소 명소 정보(이름 + 대표 작품 하나).

    예전엔 프론트가 이 값을 채우려고 명소 상세(GET /api/places/<id>/)를 한 번 더
    불렀다. 그런데 그 API는 주변 상권을 카카오에 실시간으로 물어봐서(_fetch_nearby_places)
    유독 느리다. 캡션 한 줄 때문에 메인 화면 히어로가 그만큼 늦어져서, 캡션에 필요한
    값만 명예의전당 응답에 바로 담기로 했다 (DETAIL_SPEC 6-1 #20-1, 2026-09-09 뒤집음).

    name/work.title은 context의 language에 승인된 번역이 있으면 그 값을, 없으면 한국어
    원문을 돌려준다. 뷰가 translations를 prefetch하고 context={"language": ...}를
    넣어줘야 한다(안 넣으면 항상 한국어 원문).
    """

    name = serializers.SerializerMethodField()
    work = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ["id", "name", "work"]
        read_only_fields = fields

    def get_name(self, obj):
        return pick_translated_text(obj, "name", self.context.get("language"))

    def get_work(self, obj):
        # 목업 캡션은 작품을 하나만 보여주므로 명소에 연결된 작품 중 첫 번째만 쓴다.
        # 연결된 작품이 없으면 null (캡션에 명소 이름만 나간다).
        first_link = next(iter(obj.place_works.all()), None)
        if first_link is None:
            return None
        work = first_link.work
        return {
            "title": pick_translated_text(work, "title", self.context.get("language")),
            "category": work.category,
        }


class HallOfFameResponseSerializer(serializers.Serializer):
    """GET /api/main/hall-of-fame/ 응답 형태 (PHASES/PHASE3.md 6번).

    이번 주 좋아요가 가장 많은, 사진이 있는 리뷰 하나를 review에 담아 돌려준다.
    후보가 하나도 없으면(이번 주 좋아요 데이터가 없음) review는 null이다 —
    화면이 깨지면 안 되므로 오류로 처리하지 않는다.

    place는 그 리뷰가 달린 명소의 캡션용 최소 정보다. review가 null이면 place도 null.
    """

    review = ReviewSerializer(allow_null=True)
    place = HallOfFamePlaceSerializer(allow_null=True)


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
