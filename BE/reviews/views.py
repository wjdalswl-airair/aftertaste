from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api_messages import NOT_FOUND_MESSAGE
from places.models import Place
from reviews.models import REVIEW_REPORT_HIDE_THRESHOLD, Review, ReviewLike, ReviewReport
from reviews.serializers import (
    ReviewListResponseSerializer,
    ReviewReportSerializer,
    ReviewSerializer,
    ReviewWriteSerializer,
)


def _visible_reviews(place):
    """관리자가 감추지 않은 리뷰만, 최신순으로 돌려준다."""
    return place.reviews.filter(is_hidden=False).order_by("-created_at")


class PlaceReviewListCreateView(APIView):
    """명소의 리뷰 목록 보기(로그인 불필요) / 리뷰 쓰기(로그인 필요) (DETAIL_SPEC 3-5).

    SearchView와 같은 이유로 perform_authentication을 오버라이드한다: 토큰이 무효/만료돼도
    목록 조회(GET)는 막지 않는다. POST는 그대로 IsAuthenticated가 막아준다 — 예외를
    삼키면 request.user가 AnonymousUser가 될 뿐이라, get_permissions에서 여전히
    로그인이 안 된 것으로 판단해 401(NotAuthenticated)로 막힌다.
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
        summary="명소 리뷰 목록 조회",
        description="관리자가 감추지 않은 리뷰를 최신순으로 반환한다. 로그인이 필요 없다.",
        responses={200: ReviewListResponseSerializer, 404: OpenApiResponse(description="명소 없음")},
    )
    def get(self, request, place_id):
        try:
            place = Place.objects.get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        reviews = _visible_reviews(place)
        return Response({"reviews": ReviewSerializer(reviews, many=True, context={"request": request}).data})

    @extend_schema(
        summary="리뷰 작성",
        description="별점·글(최대 500자)·사진(최대 5장)으로 리뷰를 남긴다. 로그인이 필요하다.",
        request=ReviewWriteSerializer,
        responses={
            201: OpenApiResponse(description="{ reviewId }"),
            401: OpenApiResponse(description="로그인 필요"),
            400: OpenApiResponse(description="별점 범위·글자 수·사진 장수 오류"),
            404: OpenApiResponse(description="명소 없음"),
        },
    )
    def post(self, request, place_id):
        try:
            place = Place.objects.get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        serializer = ReviewWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(member=request.user, place=place)
        return Response({"reviewId": review.id}, status=201)


class ReviewDetailView(APIView):
    """내 리뷰 고치기·지우기. 로그인이 필요하고, 작성자 본인만 할 수 있다 (DETAIL_SPEC 3-5)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="리뷰 수정",
        request=ReviewWriteSerializer,
        responses={200: None, 401: OpenApiResponse(description="로그인 필요"), 403: OpenApiResponse(description="작성자 아님")},
    )
    def patch(self, request, review_id):
        try:
            review = Review.objects.get(pk=review_id)
        except Review.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        if review.member_id != request.user.id:
            raise PermissionDenied()
        serializer = ReviewWriteSerializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=200)

    @extend_schema(
        summary="리뷰 삭제",
        responses={204: None, 401: OpenApiResponse(description="로그인 필요"), 403: OpenApiResponse(description="작성자 아님")},
    )
    def delete(self, request, review_id):
        try:
            review = Review.objects.get(pk=review_id)
        except Review.DoesNotExist:
            # 이미 지워진 리뷰를 또 지우는 경우: 오류 없이 넘어간다 (DETAIL_SPEC 3-5).
            return Response(status=204)
        if review.member_id != request.user.id:
            raise PermissionDenied()
        review.delete()
        return Response(status=204)


class ReviewLikeView(APIView):
    """리뷰 좋아요 누르기/취소. 로그인이 필요하다.

    한 사람이 같은 리뷰를 여러 번 눌러도 하나로만 센다 — 오류(409)로 처리하지 않고
    이미 눌린 상태로 조용히 넘어간다 (DETAIL_SPEC 5장 공통 예외 처리 규칙).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="리뷰 좋아요", request=None, responses={201: None, 200: None, 401: OpenApiResponse(description="로그인 필요")}
    )
    def post(self, request, review_id):
        try:
            review = Review.objects.get(pk=review_id)
        except Review.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        _, created = ReviewLike.objects.get_or_create(review=review, member=request.user)
        return Response(status=201 if created else 200)

    @extend_schema(summary="리뷰 좋아요 취소", request=None, responses={204: None, 401: OpenApiResponse(description="로그인 필요")})
    def delete(self, request, review_id):
        ReviewLike.objects.filter(review_id=review_id, member=request.user).delete()
        return Response(status=204)


class ReviewReportView(APIView):
    """리뷰 신고. 로그인이 필요하다.

    같은 사람이 같은 리뷰를 여러 번 신고해도 한 건만 접수한다. 새로 접수되면 201,
    이미 신고한 리뷰를 또 신고하면 200 — 좋아요·즐겨찾기와 같은 멱등 규약이다.
    서로 다른 사람이 REVIEW_REPORT_HIDE_THRESHOLD명 신고하면 그 순간 자동으로 숨긴다
    (DETAIL_SPEC 6-1 #13). 관리자가 확인 후 풀어준 리뷰는 다시 자동으로 숨기지 않는다 —
    신고 수가 임계값을 "막 넘어서는" 그 한 번만 처리하기 때문이다. 관리자의 수동 숨김·해제는
    그대로 admin에서 한다.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="리뷰 신고",
        request=ReviewReportSerializer,
        responses={201: None, 200: None, 401: OpenApiResponse(description="로그인 필요")},
    )
    def post(self, request, review_id):
        try:
            review = Review.objects.get(pk=review_id)
        except Review.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)
        reason = request.data.get("reason", "")
        _, created = ReviewReport.objects.get_or_create(
            review=review, member=request.user, defaults={"reason": reason}
        )
        # 신고 수가 임계값에 "딱 도달하는" 그 한 번만 자동 숨김. 그 뒤 신고(6번째~)나
        # 관리자가 풀어준 뒤의 신고로는 다시 숨기지 않는다. 신고는 삭제되지 않으므로
        # count는 created=True마다 1씩만 늘어 이 조건을 정확히 한 번 통과한다.
        if created and review.reports.count() == REVIEW_REPORT_HIDE_THRESHOLD and not review.is_hidden:
            review.is_hidden = True
            review.save(update_fields=["is_hidden"])
        return Response(status=201 if created else 200)


class MyReviewListView(APIView):
    """내가 쓴 리뷰 모아보기. 로그인이 필요하다."""

    permission_classes = [IsAuthenticated]

    @extend_schema(summary="내 리뷰 조회", responses={200: ReviewListResponseSerializer, 401: OpenApiResponse(description="로그인 필요")})
    def get(self, request):
        reviews = Review.objects.filter(member=request.user).order_by("-created_at")
        return Response({"reviews": ReviewSerializer(reviews, many=True, context={"request": request}).data})
