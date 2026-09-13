from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from main.models import Banner
from main.serializers import (
    BannerListResponseSerializer,
    BannerSerializer,
    HallOfFamePlaceSerializer,
    HallOfFameResponseSerializer,
    TopPlaceListResponseSerializer,
    TopPlaceSerializer,
)
from places.models import Place
from places.translation import resolve_language
from places.views import favorited_place_ids_for
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

    응답에는 리뷰 객체(review)와, 그 리뷰가 달린 명소의 캡션용 최소 정보(place: 이름 +
    대표 작품 하나)를 함께 담는다. 예전엔 place를 id만 주고 프론트가 GET /api/places/<id>/를
    한 번 더 불러 채웠는데, 그 API가 주변 상권을 카카오에 실시간으로 물어봐서 느려
    메인 화면 히어로가 그만큼 늦어졌다. 그래서 캡션에 필요한 값만 여기서 바로 준다
    (DETAIL_SPEC 6-1 #20-1, 2026-09-09에 2026-08-28 결정을 뒤집음).

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
            "리뷰가 달린 명소의 캡션용 정보(place: 이름 + 대표 작품 하나)도 함께 준다.\n\n"
            "이번 주 좋아요 데이터가 하나도 없으면 review와 place가 둘 다 null로 온다."
        ),
        parameters=[
            OpenApiParameter(
                "lang",
                str,
                description="place 캡션 언어 (예: en). 안 주면 로그인 회원의 언어 → 한국어 순",
            ),
        ],
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
            .select_related("member")
            .prefetch_related("photos")
            .annotate(like_count=Count("likes", distinct=True))
            .order_by("-like_count", "-created_at", "-id")
            .distinct()
            .first()
        )
        if review is None:
            return Response({"review": None, "place": None})

        # 캡션에 쓸 명소 이름·작품 제목을 번역까지 골라야 해서 translations를 함께 prefetch한다.
        # review.place는 필수 연결이라 항상 존재하지만, 방어적으로 first()로 받는다.
        place = (
            Place.objects.prefetch_related("translations", "place_works__work__translations")
            .filter(pk=review.place_id)
            .first()
        )
        language = resolve_language(request)
        return Response(
            {
                "review": ReviewSerializer(review, context={"request": request}).data,
                "place": (
                    HallOfFamePlaceSerializer(place, context={"language": language}).data
                    if place is not None
                    else None
                ),
            }
        )


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
        places = list(
            Place.objects.annotate(favorite_count=Count("favorited_by"))
            .filter(favorite_count__gt=0)
            .order_by("-favorite_count", "id")[:TOP_PLACES_COUNT]
        )
        # 카드 별을 "이미 찜함/아직 안 찜함"으로 정확히 그리게 한다 (fix/be/main-tab-favorite).
        context = {"favorited_place_ids": favorited_place_ids_for(request.user, places)}
        return Response(
            {"places": TopPlaceSerializer(places, many=True, context=context).data}
        )
