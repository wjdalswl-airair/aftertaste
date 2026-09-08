from django.db.models import Avg
from rest_framework import serializers

from favorites.models import Favorite
from places.models import Place, PlaceWork, Work
from places.translation import pick_translated_text
from reviews.serializers import ReviewSerializer


class PlaceSearchSerializer(serializers.ModelSerializer):
    """검색 결과·추천·Top10의 명소 카드에 쓰는 최소 정보. 상세 정보는 명소 상세 API(Phase 2-5) 몫이다.

    name은 context의 language에 승인된 번역이 있으면 그 값을, 없으면 한국어 원문을 돌려준다
    (뷰가 context={"language": ...}를 넣어줘야 한다. 안 넣으면 항상 한국어 원문).

    is_favorited는 "지금 로그인한 사람이 이 명소를 이미 즐겨찾기 했는지"다. 목록 뷰가
    context["favorited_place_ids"]에 그 사람의 즐겨찾기 place_id 집합을 넣어줘야 한다
    (명소마다 따로 조회하면 N+1이라 뷰에서 한 번에 모아 넘긴다). 안 넣으면 항상 False다
    — 메인 화면 카드 별이 늘 빈 별로 시작해서, 이미 찜한 곳을 다시 눌러 취소돼 버리던 문제를
    막기 위한 필드다 (fix/be/main-tab-favorite).
    """

    name = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ["id", "name", "address", "photo_url", "is_favorited"]
        read_only_fields = fields

    def get_name(self, obj):
        return pick_translated_text(obj, "name", self.context.get("language"))

    def get_is_favorited(self, obj):
        return obj.id in self.context.get("favorited_place_ids", set())


class WorkSearchSerializer(serializers.ModelSerializer):
    """검색 결과의 작품 섹션에 쓰는 최소 정보. title 번역 규칙은 PlaceSearchSerializer.name과 같다."""

    title = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = ["id", "title", "category", "poster_url"]
        read_only_fields = fields

    def get_title(self, obj):
        return pick_translated_text(obj, "title", self.context.get("language"))


class SearchResponseSerializer(serializers.Serializer):
    """GET /api/places/search/ 응답 형태."""

    places = PlaceSearchSerializer(many=True)
    works = WorkSearchSerializer(many=True)
    message = serializers.CharField(required=False)


class AutocompleteResponseSerializer(serializers.Serializer):
    """GET /api/places/search/autocomplete/ 응답 형태."""

    suggestions = serializers.ListField(child=serializers.CharField())


class PopularKeywordsResponseSerializer(serializers.Serializer):
    """GET /api/places/search/popular/ 응답 형태. 인기 검색어를 많이 검색된 순으로 담는다."""

    keywords = serializers.ListField(child=serializers.CharField())


class RecommendResponseSerializer(serializers.Serializer):
    """GET /api/places/recommend/ 응답 형태."""

    places = PlaceSearchSerializer(many=True)


class WorkDetailSerializer(serializers.ModelSerializer):
    """명소 상세에 보여줄 작품 정보 (PRD F-05: 제목, 방영 시기, 주연배우, 감독).

    title/description은 PlaceSearchSerializer.name과 같은 규칙으로 번역문을 고른다.
    """

    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = ["id", "title", "description", "category", "release_date", "main_cast", "director", "poster_url"]
        read_only_fields = fields

    def get_title(self, obj):
        return pick_translated_text(obj, "title", self.context.get("language"))

    def get_description(self, obj):
        return pick_translated_text(obj, "description", self.context.get("language"))


class PlaceWorkSerializer(serializers.ModelSerializer):
    """명소에 연결된 작품 하나 + 이 명소가 그 작품에서 나온 장면 설명."""

    work = WorkDetailSerializer(read_only=True)

    class Meta:
        model = PlaceWork
        fields = ["work", "scene_description"]
        read_only_fields = fields


class WorkPlaceSerializer(serializers.ModelSerializer):
    """작품 상세에 보여줄, 그 작품이 촬영된 명소 하나. name은 lang에 따라 번역문을 고른다."""

    name = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ["id", "name", "address", "photo_url"]
        read_only_fields = fields

    def get_name(self, obj):
        return pick_translated_text(obj, "name", self.context.get("language"))


class WorkPageSerializer(serializers.ModelSerializer):
    """GET /api/works/<id>/ 응답. 작품 정보 + 이 작품이 촬영된 명소 목록.

    title/description은 PlaceDetailSerializer.name과 같은 규칙으로 번역문을 고른다.
    places는 PlaceWork로 연결된 명소들이고, 촬영지가 없는 작품이면 빈 배열이다.
    """

    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    places = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = [
            "id",
            "title",
            "description",
            "category",
            "release_date",
            "main_cast",
            "director",
            "poster_url",
            "places",
        ]
        read_only_fields = fields

    def get_title(self, obj):
        return pick_translated_text(obj, "title", self.context.get("language"))

    def get_description(self, obj):
        return pick_translated_text(obj, "description", self.context.get("language"))

    def get_places(self, obj):
        places = sorted((pw.place for pw in obj.place_works.all()), key=lambda p: p.id)
        return WorkPlaceSerializer(places, many=True, context=self.context).data


class NearbyPlaceSerializer(serializers.Serializer):
    """카카오 장소 검색 API에서 받아온 주변 상권 하나. 우리 DB에는 저장하지 않는다."""

    place_name = serializers.CharField(allow_null=True)
    address_name = serializers.CharField(allow_null=True)
    road_address_name = serializers.CharField(allow_null=True, allow_blank=True)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    category_name = serializers.CharField(allow_null=True, allow_blank=True)


class PlaceDetailSerializer(serializers.ModelSerializer):
    """GET /api/places/<id>/ 응답. 명소 기본 정보 + 등장 작품 + 주변 상권 + 리뷰를 한 화면 분량으로 담는다.

    name/description은 PlaceSearchSerializer.name과 같은 규칙으로 번역문을 고른다.
    address/business_hours/recommended_time/photo_tips/etiquette는 번역 대상이 아니라
    항상 한국어 그대로 나간다.
    """

    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    works = PlaceWorkSerializer(source="place_works", many=True, read_only=True)
    # nearby_places는 모델 필드가 아니라, 뷰에서 카카오 API 결과를 place 객체에 임시로 붙여준 값이다.
    nearby_places = NearbyPlaceSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    review_average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = [
            "id",
            "name",
            "address",
            "photo_url",
            "business_hours",
            "recommended_time",
            "photo_tips",
            "etiquette",
            "description",
            "latitude",
            "longitude",
            "works",
            "nearby_places",
            "is_favorited",
            "reviews",
            "review_average_rating",
            "review_count",
        ]
        read_only_fields = fields

    def get_name(self, obj):
        return pick_translated_text(obj, "name", self.context.get("language"))

    def get_description(self, obj):
        return pick_translated_text(obj, "description", self.context.get("language"))

    def get_is_favorited(self, obj):
        # 로그인한 사람이면 내가 이미 즐겨찾기 했는지 표시한다 (DETAIL_SPEC 3-4).
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Favorite.objects.filter(member=request.user, place=obj).exists()

    def get_reviews(self, obj):
        reviews = obj.reviews.filter(is_hidden=False).order_by("-created_at")
        return ReviewSerializer(reviews, many=True, context=self.context).data

    def get_review_average_rating(self, obj):
        average = obj.reviews.filter(is_hidden=False).aggregate(Avg("rating"))["rating__avg"]
        return round(average, 1) if average is not None else None

    def get_review_count(self, obj):
        # 목업의 "4.7 (3,211)"처럼 별점 평균 옆에 보여줄 리뷰 개수. 감춰진 리뷰는 뺀다.
        return obj.reviews.filter(is_hidden=False).count()
