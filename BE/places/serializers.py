from rest_framework import serializers

from places.models import Place, PlaceWork, Work


class PlaceSearchSerializer(serializers.ModelSerializer):
    """검색 결과의 명소 섹션에 쓰는 최소 정보. 상세 정보는 명소 상세 API(Phase 2-5) 몫이다."""

    class Meta:
        model = Place
        fields = ["id", "name", "address", "photo_url"]
        read_only_fields = fields


class WorkSearchSerializer(serializers.ModelSerializer):
    """검색 결과의 작품 섹션에 쓰는 최소 정보."""

    class Meta:
        model = Work
        fields = ["id", "title", "category", "poster_url"]
        read_only_fields = fields


class SearchResponseSerializer(serializers.Serializer):
    """GET /api/places/search/ 응답 형태."""

    places = PlaceSearchSerializer(many=True)
    works = WorkSearchSerializer(many=True)
    message = serializers.CharField(required=False)


class AutocompleteResponseSerializer(serializers.Serializer):
    """GET /api/places/search/autocomplete/ 응답 형태."""

    suggestions = serializers.ListField(child=serializers.CharField())


class RecommendResponseSerializer(serializers.Serializer):
    """GET /api/places/recommend/ 응답 형태."""

    places = PlaceSearchSerializer(many=True)


class WorkDetailSerializer(serializers.ModelSerializer):
    """명소 상세에 보여줄 작품 정보 (PRD F-05: 제목, 방영 시기, 주연배우, 감독)."""

    class Meta:
        model = Work
        fields = ["id", "title", "category", "release_date", "main_cast", "director", "poster_url"]
        read_only_fields = fields


class PlaceWorkSerializer(serializers.ModelSerializer):
    """명소에 연결된 작품 하나 + 이 명소가 그 작품에서 나온 장면 설명."""

    work = WorkDetailSerializer(read_only=True)

    class Meta:
        model = PlaceWork
        fields = ["work", "scene_description"]
        read_only_fields = fields


class NearbyPlaceSerializer(serializers.Serializer):
    """카카오 장소 검색 API에서 받아온 주변 상권 하나. 우리 DB에는 저장하지 않는다."""

    place_name = serializers.CharField(allow_null=True)
    address_name = serializers.CharField(allow_null=True)
    road_address_name = serializers.CharField(allow_null=True, allow_blank=True)
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    category_name = serializers.CharField(allow_null=True, allow_blank=True)


class PlaceDetailSerializer(serializers.ModelSerializer):
    """GET /api/places/<id>/ 응답. 명소 기본 정보 + 등장 작품 + 주변 상권을 한 화면 분량으로 담는다."""

    works = PlaceWorkSerializer(source="place_works", many=True, read_only=True)
    # nearby_places는 모델 필드가 아니라, 뷰에서 카카오 API 결과를 place 객체에 임시로 붙여준 값이다.
    nearby_places = NearbyPlaceSerializer(many=True, read_only=True)

    class Meta:
        model = Place
        fields = [
            "id",
            "name",
            "address",
            "photo_url",
            "business_hours",
            "description",
            "latitude",
            "longitude",
            "works",
            "nearby_places",
        ]
        read_only_fields = fields
