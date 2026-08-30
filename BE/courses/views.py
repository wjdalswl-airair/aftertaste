from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api_messages import NOT_FOUND_MESSAGE
from courses.models import Course
from courses.serializers import (
    CourseListResponseSerializer,
    CourseSerializer,
    CourseWriteSerializer,
)
from places.models import Place


class PlaceCourseListCreateView(APIView):
    """명소를 기준으로 하는 코스 목록 조회(로그인 불필요) / 코스 생성(로그인 필요).

    명소 상세 화면에서 코스로 들어가는 진입점이다 (PHASES/PHASE4.md 코스 완료 기준).

    reviews.PlaceReviewListCreateView와 같은 이유로 perform_authentication을 오버라이드한다:
    토큰이 무효/만료돼도 목록 조회(GET)는 막지 않는다. POST는 IsAuthenticated가 그대로 막아준다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return super().get_permissions()

    @extend_schema(
        summary="명소 기준 코스 목록 조회",
        description="이 명소를 기준으로 만들어진 코스 목록을 반환한다. 로그인이 필요 없다.",
        responses={200: CourseListResponseSerializer, 404: OpenApiResponse(description="명소 없음")},
    )
    def get(self, request, place_id):
        try:
            place = Place.objects.get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        courses = place.courses.prefetch_related("course_places").order_by("-created_at")
        return Response({"courses": CourseSerializer(courses, many=True).data})

    @extend_schema(
        summary="코스 생성",
        description="이 명소를 기준으로 식당 1 + 카페 1 + 그 외 1로 구성된 코스를 만든다. 로그인이 필요하다.",
        request=CourseWriteSerializer,
        responses={
            201: CourseSerializer,
            400: OpenApiResponse(description="식당/카페/그 외 구성이 맞지 않음"),
            401: OpenApiResponse(description="로그인 필요"),
            404: OpenApiResponse(description="명소 없음"),
        },
    )
    def post(self, request, place_id):
        try:
            place = Place.objects.get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        serializer = CourseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save(place=place, creator=request.user)
        return Response(CourseSerializer(course).data, status=201)


class CourseDetailView(APIView):
    """코스 상세 조회(로그인 불필요) / 수정·삭제(작성자 본인만, 로그인 필요)."""

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    def get_permissions(self):
        if self.request.method == "GET":
            return super().get_permissions()
        return [IsAuthenticated()]

    @extend_schema(
        summary="코스 상세 조회",
        responses={200: CourseSerializer, 404: OpenApiResponse(description="코스 없음")},
    )
    def get(self, request, course_id):
        try:
            course = Course.objects.prefetch_related("course_places").get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        return Response(CourseSerializer(course).data)

    @extend_schema(
        summary="코스 수정",
        request=CourseWriteSerializer,
        responses={
            200: CourseSerializer,
            401: OpenApiResponse(description="로그인 필요"),
            403: OpenApiResponse(description="작성자 아님"),
            404: OpenApiResponse(description="코스 없음"),
        },
    )
    def patch(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        if course.creator_id != request.user.id:
            raise PermissionDenied()
        serializer = CourseWriteSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CourseSerializer(course).data)

    @extend_schema(
        summary="코스 삭제",
        responses={
            204: None,
            401: OpenApiResponse(description="로그인 필요"),
            403: OpenApiResponse(description="작성자 아님"),
        },
    )
    def delete(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            # 이미 지워진 코스를 또 지우는 경우: 오류 없이 넘어간다 (DETAIL_SPEC 5장 공통 규칙).
            return Response(status=204)
        if course.creator_id != request.user.id:
            raise PermissionDenied()
        course.delete()
        return Response(status=204)


class MyCourseListView(APIView):
    """내가 만든 코스 목록 (마이페이지용). 로그인이 필요하다."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="내 코스 조회",
        responses={200: CourseListResponseSerializer, 401: OpenApiResponse(description="로그인 필요")},
    )
    def get(self, request):
        courses = (
            Course.objects.filter(creator=request.user)
            .prefetch_related("course_places")
            .order_by("-created_at")
        )
        return Response({"courses": CourseSerializer(courses, many=True).data})
