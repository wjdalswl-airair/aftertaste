from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Banner
from main.serializers import (
    BannerListResponseSerializer,
    BannerSerializer,
    HallOfFameResponseSerializer,
    TopPlaceListResponseSerializer,
    TopPlaceSerializer,
)
from places.models import Place
from reviews.models import Review
from reviews.serializers import ReviewSerializer

# Top10 캐러셀에 보여줄 명소 개수 (PRD F-02, PHASES/PHASE3.md 6번).
TOP_PLACES_COUNT = 10


class BannerListView(ListAPIView):
    """메인 화면 배너 목록. 로그인 없이 볼 수 있고, 활성화된 배너만 노출 순서대로 보여준다."""

    serializer_class = BannerSerializer
    queryset = Banner.objects.filter(is_active=True)

    @extend_schema(
        summary="배너 목록 조회",
        description="활성화된 배너를 노출 순서대로 반환한다. 로그인이 필요 없다.",
        responses={200: BannerListResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"banners": serializer.data})


class HallOfFameView(APIView):
    """명예의 전당. 이번 주에 좋아요가 가장 많은, 사진이 있는 리뷰 하나를 보여준다
    (PRD F-02, PHASES/PHASE3.md 6번. 2026-08-28: 월→주로 변경, 목업 "금주의 명예의 전당").

    "그 주"는 리뷰 작성일(created_at) 기준 이번 주(월요일 0시부터)로 판단한다.
    ReviewLike에는 좋아요를 누른 시점 정보가 없어서 "좋아요를 누른 시점 기준"으로는
    애초에 계산할 수 없다. 사진이 없는 리뷰(사진을 보여주는 기능이므로)와 감춰진(is_hidden)
    리뷰는 후보에서 뺀다. 이번 주 좋아요 데이터가 하나도 없으면 review를 null로 돌려준다
    (오류로 처리하지 않음). 화면에 나가는 대표 이미지는 리뷰 사진 중 첫 번째 장이다
    (ReviewSerializer의 photos 배열 순서가 곧 제출 순서, DETAIL_SPEC 2-3).

    응답에는 리뷰 객체만 담는다(place는 id만). 목업 카드에 필요한 명소 이름·작품 제목은
    프론트엔드가 review.place id로 GET /api/places/<id>/를 한 번 더 불러서 채운다
    (DETAIL_SPEC 6-1 #20-1, 2026-08-28).

    배너·추천처럼 메인 화면 구성요소는 지금까지 전부 로그인이 필요 없었던 패턴을 따라
    로그인 여부와 상관없이 호출할 수 있게 만들었다. SearchView와 같은 이유로
    perform_authentication을 오버라이드한다: 토큰이 무효/만료돼도 조회 자체는 막지 않는다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="명예의 전당 조회",
        description=(
            "이번 주(월요일부터)에 좋아요가 가장 많은, 사진이 있는 리뷰 하나를 반환한다.\n\n"
            "이번 주 좋아요 데이터가 하나도 없으면 review가 null로 온다."
        ),
        responses={200: HallOfFameResponseSerializer},
    )
    def get(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())  # 이번 주 월요일
        review = (
            Review.objects.filter(
                is_hidden=False,
                created_at__date__gte=week_start,
                photos__isnull=False,
            )
            .annotate(like_count=Count("likes", distinct=True))
            .order_by("-like_count", "-created_at", "-id")
            .distinct()
            .first()
        )
        if review is None:
            return Response({"review": None})
        return Response({"review": ReviewSerializer(review, context={"request": request}).data})


class TopPlacesView(APIView):
    """Top10 캐러셀. 즐겨찾기가 가장 많은 명소 10곳을 보여준다 (PRD F-02, PHASES/PHASE3.md 6번).
    즐겨찾기가 하나도 없으면 빈 목록을 돌려준다(오류로 처리하지 않음).

    HallOfFameView와 같은 이유로 로그인 여부와 상관없이 호출할 수 있고,
    perform_authentication을 오버라이드해 무효/만료 토큰이어도 조회를 막지 않는다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="Top10 명소 조회",
        description="즐겨찾기가 가장 많은 명소 10곳을 즐겨찾기 수 내림차순으로 반환한다.",
        responses={200: TopPlaceListResponseSerializer},
    )
    def get(self, request):
        places = (
            Place.objects.annotate(favorite_count=Count("favorited_by"))
            .filter(favorite_count__gt=0)
            .order_by("-favorite_count", "id")[:TOP_PLACES_COUNT]
        )
        return Response({"places": TopPlaceSerializer(places, many=True).data})
