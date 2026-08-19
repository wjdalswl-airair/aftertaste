import logging

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from places.models import Place, SearchHistory, Work
from places.serializers import (
    AutocompleteResponseSerializer,
    PlaceDetailSerializer,
    PlaceSearchSerializer,
    RecommendResponseSerializer,
    SearchResponseSerializer,
    WorkSearchSerializer,
)
from places.services import haversine_distance_meters, to_decimal
from places.sources import kakao_geocoding

logger = logging.getLogger(__name__)

# 자동완성 후보 개수 제한. 문서에 정해진 값이 없어 임의로 정한 값이라 확정이 필요하다.
AUTOCOMPLETE_LIMIT = 10

# 추천 개수. PRD F-04, PHASES/PHASE2.md 2-4에서 3으로 정해짐.
RECOMMEND_COUNT = 3

NO_RESULT_MESSAGE = "검색결과가 존재하지 않습니다"
NOT_FOUND_MESSAGE = "존재하지 않습니다"

# 명소 상세의 "주변 상권" 조회 설정. 반경 1km 안에서 음식점·카페·관광명소 카테고리를
# 각각 카카오 카테고리 검색으로 가져와 합친다 (PHASES/PHASE2.md 2-5 "주변 상권 검색 기준", 2026-08-19).
NEARBY_PLACES_CATEGORY_CODES = ["FD6", "CE7", "AT4"]  # 음식점, 카페, 관광명소
NEARBY_PLACES_RADIUS_METERS = 1000
NEARBY_PLACES_LIMIT = 15

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


def _nearest_places(latitude, longitude, count):
    """좌표를 가진 명소 중 현재 위치에서 가까운 순서로 count개를 돌려준다.

    명소 수가 적어(수백~수천 건) 파이썬에서 전부 훑어 거리를 계산해도 충분하다.
    좌표가 없는 명소는 거리를 잴 수 없으므로 대상에서 뺀다.
    """
    places = list(Place.objects.filter(latitude__isnull=False, longitude__isnull=False))
    places.sort(key=lambda p: haversine_distance_meters(latitude, longitude, p.latitude, p.longitude))
    return places[:count]


def _random_places(count):
    """위치 정보가 없을 때(위치 권한 거부) 명소를 무작위로 count개 고른다."""
    return list(Place.objects.order_by("?")[:count])


class RecommendationView(APIView):
    """위치기반 명소 추천. 로그인 여부와 상관없이 호출할 수 있다 (PRD F-04).

    - lat, lng를 둘 다 보내면(위치 권한 허용) 그 위치에서 가장 가까운 명소 3곳을 추천한다.
    - lat, lng를 안 보내거나 숫자가 아니면(위치 권한 거부) 명소 3곳을 무작위로 추천한다.
      즐겨찾기 기준으로 하고 싶었지만 즐겨찾기 모델이 Phase 3에 생기므로, Phase 2에서는
      무작위로 추천한다 (PHASES/PHASE2.md 2-4, 2026-08-19 결정).
    - 로그인 + 검색이력 반영 개인화는 Phase 3 범위라 여기서 다루지 않는다.

    SearchView와 같은 이유로 perform_authentication을 오버라이드한다: 이 API는
    로그인이 필요 없으므로, 토큰이 무효/만료돼도 추천 자체는 막지 않는다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="위치기반 명소 추천",
        description=(
            "lat, lng를 함께 보내면 그 위치에서 가장 가까운 명소 3곳을 추천한다.\n\n"
            "lat, lng를 안 보내면(위치 권한 거부) 명소 3곳을 무작위로 추천한다."
        ),
        parameters=[
            OpenApiParameter("lat", float, description="현재 위도 (선택)"),
            OpenApiParameter("lng", float, description="현재 경도 (선택)"),
        ],
        responses={200: RecommendResponseSerializer},
    )
    def get(self, request):
        latitude, lat_ok = to_decimal(request.query_params.get("lat"))
        longitude, lng_ok = to_decimal(request.query_params.get("lng"))

        if lat_ok and lng_ok and latitude is not None and longitude is not None:
            places = _nearest_places(latitude, longitude, RECOMMEND_COUNT)
        else:
            places = _random_places(RECOMMEND_COUNT)

        return Response({"places": PlaceSearchSerializer(places, many=True).data})


def _fetch_nearby_places(place):
    """명소 좌표를 기준으로 카카오 카테고리 검색 API를 호출해 주변 상권 목록을 가져온다.

    음식점(FD6)·카페(CE7)·관광명소(AT4) 세 카테고리를 각각 따로 검색해서 합친다.
    좌표가 없는 명소는 검색할 수 없으므로 빈 목록을 준다.
    카테고리 하나가 실패해도(네트워크 오류, 타임아웃, 키 미설정 등) 나머지 카테고리와
    명소 상세 전체는 깨지지 않도록, 카테고리별로 예외를 잡고 계속 진행한다.
    """
    if place.latitude is None or place.longitude is None:
        return []

    results = []
    seen_keys = set()
    for category_code in NEARBY_PLACES_CATEGORY_CODES:
        try:
            category_results = kakao_geocoding.search_by_category(
                category_code,
                x=float(place.longitude),
                y=float(place.latitude),
                radius=NEARBY_PLACES_RADIUS_METERS,
                size=NEARBY_PLACES_LIMIT,
            )
        except Exception:
            logger.warning(
                "카카오 주변 상권 조회 실패 (place_id=%s, category=%s)", place.id, category_code, exc_info=True
            )
            continue

        for item in category_results:
            # 같은 장소가 여러 카테고리에 겹쳐 나올 수 있어 중복을 뺀다.
            # 카카오가 준 고유 id가 있으면 그걸 쓰고, 없으면 이름+주소로 판단한다.
            dedup_key = item.get("id") or (item.get("place_name"), item.get("address_name"))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            results.append(item)

    return results[:NEARBY_PLACES_LIMIT]


class PlaceDetailView(APIView):
    """명소 상세. 로그인 여부와 상관없이 호출할 수 있다 (PRD F-05).

    한 화면에 명소 기본 정보 + 등장 작품(장면 설명 포함) + 주변 상권을 함께 내려준다.
    주변 상권은 저장해두지 않고, 이 요청을 받을 때마다 카카오 장소 검색 API를 대신
    호출해서(프록시) 받아온 결과를 그대로 붙여준다 (DETAIL_SPEC 2-2, PHASES/PHASE2.md 2-5).

    SearchView와 같은 이유로 perform_authentication을 오버라이드한다: 토큰이 무효/만료돼도
    상세 조회 자체는 막지 않는다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="명소 상세",
        description=(
            "명소 기본 정보, 등장 작품 목록(작품별 장면 설명 포함), 주변 상권을 한 번에 반환한다.\n\n"
            "주변 상권은 명소 좌표를 기준으로 카카오 장소 검색 API를 그때그때 호출해서 가져온다."
        ),
        responses={
            200: PlaceDetailSerializer,
            404: OpenApiResponse(description="해당 명소가 존재하지 않음"),
        },
    )
    def get(self, request, place_id):
        try:
            place = Place.objects.prefetch_related("place_works__work").get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)

        # nearby_places는 모델 필드가 아니라, 카카오 API에서 받아온 결과를 직렬화 직전에
        # 임시로 붙여주는 값이다 (PlaceDetailSerializer 참고).
        place.nearby_places = _fetch_nearby_places(place)

        return Response(PlaceDetailSerializer(place).data)
