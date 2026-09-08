from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api_messages import NOT_FOUND_MESSAGE
from courses.ai_recommendation import CourseAiError, recommend_course
from courses.models import Course, CoursePlace
from courses.serializers import (
    CourseListResponseSerializer,
    CourseSerializer,
    CourseWriteSerializer,
)
from places.models import Place

# 주변 상권 조회는 명소 상세와 똑같은 로직을 쓴다 (카카오 카테고리 검색 프록시).
from places.views import _fetch_nearby_places


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


class PlaceCourseAiRecommendView(APIView):
    """명소를 기준으로 Claude가 코스를 자동으로 만들어 준다 (DETAIL_SPEC 6-1 #31).

    명소 상세의 "이 장소로 AI 코스 추천받기" 버튼이 호출한다. 로그인이 필요하고,
    성공하면 만들어진 코스를 코스 생성(POST)과 똑같은 형태로 201에 담아 준다.

    Claude는 주변 상권 후보 중에서 식당 1 + 카페 1 + 그 외 1을 고르고 순서·제목·소개만
    정한다. 이미 이 명소에 코스가 있으면 만들지 않는다 (프론트가 그 코스로 보내주므로
    정상 흐름에서는 여기까지 오지 않는다).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="AI 코스 추천",
        description=(
            "이 명소를 기준으로 주변 상권 중에서 Claude가 식당 1 + 카페 1 + 그 외 1을 골라 "
            "코스를 만든다. 로그인이 필요하다."
        ),
        request=None,
        responses={
            201: CourseSerializer,
            400: OpenApiResponse(description="이미 코스가 있는 명소"),
            401: OpenApiResponse(description="로그인 필요"),
            404: OpenApiResponse(description="명소 없음"),
            422: OpenApiResponse(description="주변에 후보가 부족함"),
            503: OpenApiResponse(description="AI 호출 실패"),
        },
    )
    def post(self, request, place_id):
        try:
            place = Place.objects.get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)

        if place.courses.exists():
            return Response(
                {"detail": "이미 코스가 있는 명소입니다. 기존 코스를 확인해 주세요."},
                status=400,
            )

        nearby_places = _fetch_nearby_places(place)
        try:
            result = recommend_course(place, nearby_places)
        except CourseAiError as exc:
            status_code = 422 if exc.reason == "no_candidates" else 503
            return Response({"detail": str(exc)}, status=status_code)

        with transaction.atomic():
            course = Course.objects.create(
                place=place,
                creator=request.user,
                title=result["title"],
                description=result["description"],
            )
            CoursePlace.objects.bulk_create(
                [CoursePlace(course=course, **place_data) for place_data in result["places"]]
            )

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
            204: None,
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
        # 수정 성공 시 본문 없이 204 (다른 PATCH 엔드포인트와 규약 통일).
        # 갱신된 코스가 필요하면 GET /api/courses/<id>/로 다시 조회한다.
        return Response(status=204)

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
