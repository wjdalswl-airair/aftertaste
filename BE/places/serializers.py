from rest_framework import serializers

from places.models import Place, Work


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
