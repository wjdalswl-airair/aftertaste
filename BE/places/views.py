from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from places.models import Place, SearchHistory, Work
from places.serializers import (
    AutocompleteResponseSerializer,
    PlaceSearchSerializer,
    SearchResponseSerializer,
    WorkSearchSerializer,
)

# 자동완성 후보 개수 제한. 문서에 정해진 값이 없어 임의로 정한 값이라 확정이 필요하다.
AUTOCOMPLETE_LIMIT = 10

NO_RESULT_MESSAGE = "검색결과가 존재하지 않습니다"

# 구분 조회 값. WORK는 드라마+영화 전부, DRAMA/MOVIE는 해당 구분만.
VALID_SEARCH_TYPES = {"", "WORK", "DRAMA", "MOVIE"}


def _search_places(keyword):
    """명소 이름(원문 + 번역문)에서 비슷한 것까지 찾는다."""

    return (
        Place.objects.filter(
            Q(name__icontains=keyword)
            | Q(name__trigram_similar=keyword)
            | Q(translations__name__icontains=keyword)
            | Q(translations__name__trigram_similar=keyword)
        )
        .annotate(similarity=TrigramSimilarity("name", keyword))
        .distinct()
        .order_by("-similarity", "name")
    )


def _search_works(keyword, category=None):
    """작품 제목(원문 + 번역문)에서 비슷한 것까지 찾는다. category를 주면 그 구분만 본다."""

    qs = Work.objects.filter(
        Q(title__icontains=keyword)
        | Q(title__trigram_similar=keyword)
        | Q(translations__title__icontains=keyword)
        | Q(translations__title__trigram_similar=keyword)
    )
    if category:
        qs = qs.filter(category=category)
    return qs.annotate(similarity=TrigramSimilarity("title", keyword)).distinct().order_by("-similarity", "title")


class SearchView(APIView):
    """통합검색 + 구분 조회. 로그인 여부와 상관없이 호출할 수 있다.

    - type을 안 주면 명소 + 작품을 함께 찾아 섹션으로 나눠 반환한다(통합검색).
    - type=WORK/DRAMA/MOVIE면 작품만, 그중에서도 드라마·영화만 골라 본다.
    - 로그인한 사용자가 검색하면 검색어를 SearchHistory에 남긴다(최근 검색어 자료).

    LocaleView와 같은 이유로 perform_authentication을 오버라이드한다: 이 API는
    로그인이 필요 없으므로, 토큰이 무효/만료돼도 검색 자체는 막지 않고 비로그인
    사용자와 동일하게(검색 기록만 안 남기고) 처리한다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="통합검색 / 구분 조회",
        description=(
            "명소 + 작품을 함께 검색하고 결과를 명소/작품 섹션으로 나눠 반환한다.\n\n"
            "- q: 검색어 (필수, 비어 있으면 400)\n"
            "- type: WORK(작품만) / DRAMA(드라마만) / MOVIE(영화만). 안 주면 통합검색.\n\n"
            "저장된 번역 이름까지 함께 찾고, 오타·끝글자 누락도 잡아준다."
        ),
        parameters=[
            OpenApiParameter("q", str, description="검색어"),
            OpenApiParameter("type", str, description="WORK / DRAMA / MOVIE (선택)"),
        ],
        responses={
            200: SearchResponseSerializer,
            400: OpenApiResponse(description="검색어가 비었거나 type 값이 잘못됨"),
        },
    )
    def get(self, request):
        keyword = request.query_params.get("q", "").strip()
        if not keyword:
            return Response({"detail": "검색어를 입력해주세요"}, status=400)

        search_type = request.query_params.get("type", "").strip().upper()
        if search_type not in VALID_SEARCH_TYPES:
            return Response({"detail": "지원하지 않는 구분입니다"}, status=400)

        if search_type == "":
            places_qs = _search_places(keyword)
            works_qs = _search_works(keyword)
        elif search_type == "WORK":
            places_qs = Place.objects.none()
            works_qs = _search_works(keyword)
        else:  # DRAMA / MOVIE
            places_qs = Place.objects.none()
            works_qs = _search_works(keyword, category=search_type)

        data = {
            "places": PlaceSearchSerializer(places_qs, many=True).data,
            "works": WorkSearchSerializer(works_qs, many=True).data,
        }
        if not data["places"] and not data["works"]:
            data["message"] = NO_RESULT_MESSAGE

        if request.user.is_authenticated:
            # 검색 자체는 전체 검색어로 하되, 이력 저장은 CharField 길이(200자)에 맞춰 잘라서 저장한다.
            SearchHistory.objects.create(member=request.user, keyword=keyword[:200])

        return Response(data)


class SearchAutocompleteView(APIView):
    """검색어를 치는 도중 이름 후보를 보여준다. 로그인 여부와 상관없이 호출할 수 있다."""

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="검색 자동완성",
        description="입력 중인 글자로 시작/포함하는 명소·작품 이름 후보를 보여준다.",
        parameters=[OpenApiParameter("q", str, description="입력 중인 검색어")],
        responses={200: AutocompleteResponseSerializer},
    )
    def get(self, request):
        keyword = request.query_params.get("q", "").strip()
        if not keyword:
            return Response({"suggestions": []})

        place_names = (
            Place.objects.filter(Q(name__icontains=keyword) | Q(translations__name__icontains=keyword))
            .values_list("name", flat=True)
            .distinct()
        )
        work_titles = (
            Work.objects.filter(Q(title__icontains=keyword) | Q(translations__title__icontains=keyword))
            .values_list("title", flat=True)
            .distinct()
        )

        suggestions = list(dict.fromkeys(list(place_names) + list(work_titles)))[:AUTOCOMPLETE_LIMIT]
        return Response({"suggestions": suggestions})
