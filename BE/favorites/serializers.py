from rest_framework import serializers

from favorites.models import Favorite
from places.serializers import PlaceSearchSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    """내 즐겨찾기 목록에 보여줄 명소 정보."""

    place = PlaceSearchSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "place", "created_at"]
        read_only_fields = fields
