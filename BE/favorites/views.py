from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Course
from favorites.models import Favorite
from favorites.serializers import FavoriteSerializer
from places.models import Place

NOT_FOUND_MESSAGE = "존재하지 않습니다"


class MyFavoriteListView(APIView):
    """내 즐겨찾기 목록. 명소·코스를 함께 보여준다. 로그인이 필요하다 (DETAIL_SPEC 3-4, PHASES/PHASE4.md 코스)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 즐겨찾기 조회",
        responses={200: FavoriteSerializer(many=True), 401: OpenApiResponse(description="로그인 필요")},
    )
    def get(self, request):
        favorites = (
            Favorite.objects.filter(member=request.user)
            .select_related("place", "course")
            .prefetch_related("course__course_places")
            .order_by("-created_at")
        )
        return Response({"favorites": FavoriteSerializer(favorites, many=True).data})


class PlaceFavoriteView(APIView):
    """명소 즐겨찾기 추가/취소. 로그인이 필요하다 (DETAIL_SPEC 3-4).

    같은 명소를 두 번 저장해도 오류 없이 이미 저장된 상태로 처리하고, 저장하지 않은
    명소를 취소해도 오류 없이 넘어간다 — "이미 한 일을 또 함"에 대한 공통 규칙(DETAIL_SPEC 5장)을
    따른다.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="명소 즐겨찾기 추가",
        request=None,
        responses={201: None, 200: None, 401: OpenApiResponse(description="로그인 필요"), 404: OpenApiResponse(description="명소 없음")},
    )
    def post(self, request, place_id):
        try:
            place = Place.objects.get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        _, created = Favorite.objects.get_or_create(member=request.user, place=place)
        return Response(status=201 if created else 200)

    @extend_schema(
        summary="명소 즐겨찾기 취소",
        request=None,
        responses={204: None, 401: OpenApiResponse(description="로그인 필요")},
    )
    def delete(self, request, place_id):
        Favorite.objects.filter(member=request.user, place_id=place_id).delete()
        return Response(status=204)


class CourseFavoriteView(APIView):
    """코스 즐겨찾기 추가/취소. 로그인이 필요하다 (PHASES/PHASE4.md 코스).

    PlaceFavoriteView와 같은 멱등 규칙을 따른다: 두 번 저장해도 오류 없이 이미 저장된
    상태로 처리하고, 저장하지 않은 코스를 취소해도 오류 없이 넘어간다.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="코스 즐겨찾기 추가",
        request=None,
        responses={201: None, 200: None, 401: OpenApiResponse(description="로그인 필요"), 404: OpenApiResponse(description="코스 없음")},
    )
    def post(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        _, created = Favorite.objects.get_or_create(member=request.user, course=course)
        return Response(status=201 if created else 200)

    @extend_schema(
        summary="코스 즐겨찾기 취소",
        request=None,
        responses={204: None, 401: OpenApiResponse(description="로그인 필요")},
    )
    def delete(self, request, course_id):
        Favorite.objects.filter(member=request.user, course_id=course_id).delete()
        return Response(status=204)
