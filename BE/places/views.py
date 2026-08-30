import logging
from datetime import timedelta

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api_messages import NOT_FOUND_MESSAGE
from favorites.models import Favorite
from places.models import Place, PlaceWork, SearchHistory, Work
from reviews.models import Review
from places.serializers import (
    AutocompleteResponseSerializer,
    PlaceDetailSerializer,
    PlaceSearchSerializer,
    PopularKeywordsResponseSerializer,
    RecommendResponseSerializer,
    SearchResponseSerializer,
    WorkSearchSerializer,
)
from places.services import haversine_distance_meters, to_decimal
from places.sources import kakao_geocoding
from places.translation import pick_translated_text, resolve_language

logger = logging.getLogger(__name__)

# 자동완성 후보 개수 제한. 문서에 정해진 값이 없어 임의로 정한 값이라 확정이 필요하다.
AUTOCOMPLETE_LIMIT = 10

# 추천(인기) 검색어 설정 (docs/DETAIL_SPEC.md 2-5, 6-1 #23, 2026-08-28 확정).
# 최근 30일 검색 기록을 집계해 상위 5개를 보여준다. 1회만 검색된 말도 후보에 넣는다.
POPULAR_KEYWORDS_DAYS = 30
POPULAR_KEYWORDS_LIMIT = 5

# 추천 개수. PRD F-04, PHASES/PHASE2.md 2-4에서 3으로 정해짐.
RECOMMEND_COUNT = 3

# 로그인한 사용자의 개인화 추천에서 가산점을 계산할 후보 풀 크기. 문서에 정해진 값이
# 없어 임의로 정했다 - "거리 우선 + 인기도 보너스" 방식이라 후보를 넉넉히 뽑아야
# 거리는 가깝지만 가산점이 높은 곳이 상위 3곳 안에 들어올 여지가 생긴다
# (PHASE3.md 3번, 2026-08-19 사용자 확인).
RECOMMEND_CANDIDATE_POOL = 10

# 개인화 추천 가산점 가중치. 정확한 공식은 문서에 없어 임의로 정했다(자기신고, 2026-08-19).
# - 검색이력 키워드가 명소 이름/등장 작품 제목에 걸리면 키워드 하나당 5점을 준다.
#   "검색해서 관심을 보인 것"이 즐겨찾기·리뷰 한 건보다 더 강한 선호 신호라고 보고
#   즐겨찾기·리뷰 가중치보다 크게 잡았다.
# - 즐겨찾기 수·리뷰 수는 1건당 1점씩 그대로 더한다(인기도 보너스).
KEYWORD_MATCH_SCORE = 5
FAVORITE_SCORE_WEIGHT = 1
REVIEW_SCORE_WEIGHT = 1

NO_RESULT_MESSAGE = "검색결과가 존재하지 않습니다"

# 명소 상세의 "주변 상권" 조회 설정. 반경 1km 안에서 음식점·카페·관광명소 카테고리를
# 각각 카카오 카테고리 검색으로 가져와 합친다 (PHASES/PHASE2.md 2-5 "주변 상권 검색 기준", 2026-08-19).
NEARBY_PLACES_CATEGORY_CODES = ["FD6", "CE7", "AT4"]  # 음식점, 카페, 관광명소
NEARBY_PLACES_RADIUS_METERS = 1000
NEARBY_PLACES_LIMIT = 15

# 구분 조회 값. WORK는 드라마+영화 전부, DRAMA/MOVIE는 해당 구분만.
VALID_SEARCH_TYPES = {"", "WORK", "DRAMA", "MOVIE"}


def _search_places(keyword):
    """명소 이름(원문 + 번역문)에서 비슷한 것까지 찾는다.

    is_approved가 안 된 번역까지 검색 대상에 포함한다 — 여기서 뒤지는 건 "찾을 수 있는지"이지
    "무엇을 보여줄지"가 아니다. 결과에 실제로 노출되는 이름은 PlaceSearchSerializer가
    pick_translated_text로 승인된 번역만 고르므로, 미승인 텍스트가 사용자에게 그대로
    보이는 일은 없다. 승인 여부까지 걸러버리면 "번역은 됐는데 아직 승인 전"인 명소가
    번역명으로는 검색이 안 되는 빈틈이 생긴다.

    translations를 prefetch해서, 검색 결과를 직렬화할 때(pick_translated_text) 명소마다
    추가 쿼리가 나가지 않게 한다.
    """

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
        .prefetch_related("translations")
    )


def _search_works(keyword, category=None):
    """작품 제목(원문 + 번역문)에서 비슷한 것까지 찾는다. category를 주면 그 구분만 본다.

    미승인 번역까지 검색 대상에 포함하는 이유는 _search_places와 같다.
    """

    qs = Work.objects.filter(
        Q(title__icontains=keyword)
        | Q(title__trigram_similar=keyword)
        | Q(translations__title__icontains=keyword)
        | Q(translations__title__trigram_similar=keyword)
    )
    if category:
        qs = qs.filter(category=category)
    return (
        qs.annotate(similarity=TrigramSimilarity("title", keyword))
        .distinct()
        .order_by("-similarity", "title")
        .prefetch_related("translations")
    )


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
            OpenApiParameter("lang", str, description="응답 언어 (예: en). 안 주면 로그인 회원의 언어 → 한국어 순"),
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

        language = resolve_language(request)
        context = {"language": language}
        data = {
            "places": PlaceSearchSerializer(places_qs, many=True, context=context).data,
            "works": WorkSearchSerializer(works_qs, many=True, context=context).data,
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
        parameters=[
            OpenApiParameter("q", str, description="입력 중인 검색어"),
            OpenApiParameter("lang", str, description="응답 언어 (예: en). 안 주면 로그인 회원의 언어 → 한국어 순"),
        ],
        responses={200: AutocompleteResponseSerializer},
    )
    def get(self, request):
        keyword = request.query_params.get("q", "").strip()
        if not keyword:
            return Response({"suggestions": []})

        language = resolve_language(request)

        places = (
            Place.objects.filter(Q(name__icontains=keyword) | Q(translations__name__icontains=keyword))
            .distinct()
            .prefetch_related("translations")
        )
        works = (
            Work.objects.filter(Q(title__icontains=keyword) | Q(translations__title__icontains=keyword))
            .distinct()
            .prefetch_related("translations")
        )

        place_names = [pick_translated_text(place, "name", language) for place in places]
        work_titles = [pick_translated_text(work, "title", language) for work in works]

        suggestions = list(dict.fromkeys(place_names + work_titles))[:AUTOCOMPLETE_LIMIT]
        return Response({"suggestions": suggestions})


class PopularKeywordsView(APIView):
    """추천(인기) 검색어. 로그인 여부와 상관없이 호출할 수 있다 (DETAIL_SPEC 2-5, 6-1 #23).

    관리자가 손으로 고르지 않고, 최근 30일 검색 기록(SearchHistory)을 집계해
    많이 검색된 순서로 상위 5개를 돌려준다. 검색 기록은 로그인한 사용자 것만 쌓이므로
    (비로그인 검색어는 저장하지 않음, SearchView 참고) 집계 대상도 그 범위다.
    검색 기록이 아직 없으면 빈 목록을 준다(오류 아님).

    SearchView와 같은 이유로 perform_authentication을 오버라이드한다: 이 API는
    로그인이 필요 없으므로, 토큰이 무효/만료돼도 조회 자체는 막지 않는다.
    """

    def perform_authentication(self, request):
        try:
            request.user
        except AuthenticationFailed:
            pass

    @extend_schema(
        summary="추천(인기) 검색어",
        description="최근 30일 검색 기록을 집계해 많이 검색된 순으로 상위 5개를 반환한다.",
        responses={200: PopularKeywordsResponseSerializer},
    )
    def get(self, request):
        since = timezone.now() - timedelta(days=POPULAR_KEYWORDS_DAYS)
        rows = (
            SearchHistory.objects.filter(searched_at__gte=since)
            .values("keyword")
            .annotate(search_count=Count("id"))
            .order_by("-search_count", "keyword")[:POPULAR_KEYWORDS_LIMIT]
        )
        return Response({"keywords": [row["keyword"] for row in rows]})


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


def _personalized_places(member, latitude, longitude, count):
    """로그인한 사용자를 위한 "거리 우선 + 인기도 보너스" 추천 (PHASE3.md 3번, 2026-08-19 확정).

    1. 현재 위치에서 가까운 명소 후보를 넉넉히(RECOMMEND_CANDIDATE_POOL개) 뽑는다.
    2. 후보 안에서, 회원의 검색이력 키워드와 연관된 명소(이름 또는 등장 작품 제목에
       키워드가 포함) + 즐겨찾기 수 + 리뷰 수(감춰지지 않은 것만)에 가산점을 준다.
    3. 가산점 합계로 정렬해 상위 count개를 돌려준다.

    동점 처리(결정론 보장): 가산점이 같으면 거리가 가까운 쪽을, 거리도 같으면 id가
    작은 쪽을 앞에 둔다. 후보 풀 자체가 거리 기준으로 뽑히므로 "가깝지만 안 맞는 곳"이
    완전히 배제되지는 않는다.
    """
    candidates = _nearest_places(latitude, longitude, RECOMMEND_CANDIDATE_POOL)
    if not candidates:
        return candidates

    candidate_ids = [place.id for place in candidates]

    keywords = list(
        SearchHistory.objects.filter(member=member).values_list("keyword", flat=True).distinct()
    )
    keywords_lower = [kw.lower() for kw in keywords if kw]

    favorite_counts = dict(
        Favorite.objects.filter(place_id__in=candidate_ids)
        .values("place_id")
        .annotate(count=Count("id"))
        .values_list("place_id", "count")
    )
    review_counts = dict(
        Review.objects.filter(place_id__in=candidate_ids, is_hidden=False)
        .values("place_id")
        .annotate(count=Count("id"))
        .values_list("place_id", "count")
    )

    # 명소마다 연결된 작품 제목을 미리 모아둔다 (후보별로 매번 쿼리하지 않기 위해).
    work_titles_by_place = {}
    for place_work in PlaceWork.objects.filter(place_id__in=candidate_ids).select_related("work"):
        work_titles_by_place.setdefault(place_work.place_id, []).append(place_work.work.title)

    def keyword_match_count(place):
        if not keywords_lower:
            return 0
        name_lower = place.name.lower()
        work_titles_lower = [title.lower() for title in work_titles_by_place.get(place.id, [])]
        matches = 0
        for kw in keywords_lower:
            if kw in name_lower or any(kw in title for title in work_titles_lower):
                matches += 1
        return matches

    distances = {
        place.id: haversine_distance_meters(latitude, longitude, place.latitude, place.longitude)
        for place in candidates
    }

    def score(place):
        return (
            keyword_match_count(place) * KEYWORD_MATCH_SCORE
            + favorite_counts.get(place.id, 0) * FAVORITE_SCORE_WEIGHT
            + review_counts.get(place.id, 0) * REVIEW_SCORE_WEIGHT
        )

    ranked = sorted(candidates, key=lambda place: (-score(place), distances[place.id], place.id))
    return ranked[:count]


class RecommendationView(APIView):
    """위치기반 명소 추천. 로그인 여부와 상관없이 호출할 수 있다 (PRD F-04).

    - lat, lng를 둘 다 보내면(위치 권한 허용):
        - 로그인한 사용자는 "거리 우선 + 인기도 보너스" 개인화 추천을 받는다
          (검색이력·즐겨찾기·리뷰 개수 반영, _personalized_places 참고. PHASE3.md 3번).
        - 비로그인 사용자는 Phase 2와 동일하게 그 위치에서 가장 가까운 명소 3곳을 추천받는다.
    - lat, lng를 안 보내거나 숫자가 아니면(위치 권한 거부) 로그인 여부와 상관없이 명소
      3곳을 무작위로 추천한다. "위치 권한을 거부했을 경우 비로그인 상태의 추천과
      동일하다"(PRD F-04)는 규칙을 그대로 따른다.

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
            OpenApiParameter("lang", str, description="응답 언어 (예: en). 안 주면 로그인 회원의 언어 → 한국어 순"),
        ],
        responses={200: RecommendResponseSerializer},
    )
    def get(self, request):
        latitude, lat_ok = to_decimal(request.query_params.get("lat"))
        longitude, lng_ok = to_decimal(request.query_params.get("lng"))

        if lat_ok and lng_ok and latitude is not None and longitude is not None:
            if request.user.is_authenticated:
                places = _personalized_places(request.user, latitude, longitude, RECOMMEND_COUNT)
            else:
                places = _nearest_places(latitude, longitude, RECOMMEND_COUNT)
        else:
            places = _random_places(RECOMMEND_COUNT)

        # SearchView·PlaceDetailView와 같은 방식으로 응답 언어를 정한다: ?lang= → 로그인
        # 회원의 언어 → 한국어 원문. 이걸 안 넘기면 추천 목록만 항상 한국어로 나갔다.
        language = resolve_language(request)
        return Response(
            {"places": PlaceSearchSerializer(places, many=True, context={"language": language}).data}
        )


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

    한 화면에 명소 기본 정보 + 등장 작품(장면 설명 포함) + 주변 상권 + 리뷰 목록·별점 평균을
    함께 내려준다. 주변 상권은 저장해두지 않고, 이 요청을 받을 때마다 카카오 장소 검색 API를
    대신 호출해서(프록시) 받아온 결과를 그대로 붙여준다 (DETAIL_SPEC 2-2, PHASES/PHASE2.md 2-5).
    로그인한 사람이면 내가 이미 즐겨찾기 했는지(is_favorited)도 함께 보여준다 (PHASE3 1번).

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
        parameters=[
            OpenApiParameter("lang", str, description="응답 언어 (예: en). 안 주면 로그인 회원의 언어 → 한국어 순"),
        ],
        responses={
            200: PlaceDetailSerializer,
            404: OpenApiResponse(description="해당 명소가 존재하지 않음"),
        },
    )
    def get(self, request, place_id):
        try:
            place = Place.objects.prefetch_related(
                "translations", "place_works__work__translations"
            ).get(pk=place_id)
        except Place.DoesNotExist:
            return Response({"detail": NOT_FOUND_MESSAGE}, status=404)

        # nearby_places는 모델 필드가 아니라, 카카오 API에서 받아온 결과를 직렬화 직전에
        # 임시로 붙여주는 값이다 (PlaceDetailSerializer 참고).
        place.nearby_places = _fetch_nearby_places(place)

        language = resolve_language(request)
        return Response(
            PlaceDetailSerializer(place, context={"request": request, "language": language}).data
        )
