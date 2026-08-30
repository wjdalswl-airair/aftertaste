from rest_framework import serializers

from courses.serializers import CourseSerializer
from favorites.models import Favorite
from places.serializers import PlaceSearchSerializer


class FavoriteSerializer(serializers.ModelSerializer):
    """내 즐겨찾기 목록에 보여줄 정보. type으로 명소(PLACE)/코스(COURSE)를 구분한다.

    place/course 둘 중 채워진 쪽만 값이 나가고, 나머지 하나는 null이다 (DRF는 obj.place가
    None이면 자동으로 null 처리한다).
    """

    type = serializers.SerializerMethodField()
    place = PlaceSearchSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "type", "place", "course", "created_at"]
        read_only_fields = fields

    def get_type(self, obj):
        return "PLACE" if obj.place_id else "COURSE"


class FavoriteListResponseSerializer(serializers.Serializer):
    """즐겨찾기 목록 응답 형태. 배열을 그대로 주지 않고 favorites 키로 감싼다
    (main 앱의 *ResponseSerializer와 같은 방식). 뷰 응답 모양과 Swagger 문서를 맞춘다."""

    favorites = FavoriteSerializer(many=True)
