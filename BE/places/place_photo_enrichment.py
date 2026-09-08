"""DB에 있는 명소(Place)의 대표 사진(photo_url)을 외부 소스에서 채우는 서비스 계층.

소스는 두 곳이다. 둘 다 아래 규칙은 똑같고, 실제 API 호출 모듈만 다르다.
- TourAPI (places/sources/tour_api.py) — 등록된 관광지·음식점 위주. 1순위.
- 한국어 위키백과 (places/sources/wikimedia.py) — TourAPI로 못 채운 명소 보강. 2순위.

여기서 하는 일:
1. 검색 결과 중에서 "우리 Place와 같은 장소"를 가려낸다 (pick_photo_match).
   이름이 정확히 일치하고, 좌표가 있으면 거리가 가까운 후보만 인정한다 — 애매하면
   채우지 않는다. 틀린 사진이 빈 값보다 나쁘다 (work_enrichment.pick_tmdb_match와 같은 원칙).
2. 매칭에 성공하면 그 소스의 원본 번호(TourAPI content_id / 위키백과 pageid)를
   PlaceSource(source="TOUR_API" 또는 "WIKIMEDIA")에 남긴다. 다시 실행할 때는 이름으로
   재검색하지 않고 그 번호로 바로 대표 이미지를 받는다 (매칭이 흔들리거나 잘못 붙는 것을 막는다).
3. 대표 이미지를 Place.photo_url에 반영한다. photo_url은 원래 관리자가 채우는 값이라
   (models.py 참고) 비어 있을 때만 넣고, 채워져 있으면 --overwrite를 줄 때만 덮어쓴다.

이 모듈은 소스 API 응답을 판단·저장만 한다. 두 소스 모듈은 같은 함수 이름
(search_keyword, get_detail)과 같은 dict 모양을 내주므로 아래 로직이 그대로 공유된다.
"""

import logging
import re

from places.models import PlaceSource
from places.services import haversine_distance_meters
from places.sources import tour_api, wikimedia

logger = logging.getLogger(__name__)

# PlaceSource.source 값. KCISA·GYEONGGI_DATA_DREAM과 달리 명소의 "출처"가 아니라
# "대표 사진을 어디서 가져왔는지"지만, (source, source_id) 구조가 그대로 맞아 재사용한다.
TOUR_API_SOURCE = "TOUR_API"
WIKIMEDIA_SOURCE = "WIKIMEDIA"

# 매칭 실패("맞는 관광정보 없음")도 PlaceSource에 남겨서, 다시 실행할 때 같은 명소를
# 또 검색하지 않게 한다. source_id는 (source, source_id) 유일 제약 때문에 명소별로 다르게
# "__no_match__<place_id>" 형태로 둔다. --overwrite로 재시도할 수 있다.
NO_MATCH_PREFIX = "__no_match__"

# TourAPI가 채우는 Place 필드. 지금은 대표 이미지 하나뿐이다.
FILLABLE_FIELDS = ("photo_url",)

# 우리 Place 좌표와 TourAPI 후보 좌표가 이 거리(미터)보다 멀면 다른 장소로 본다.
# Place 좌표는 KCISA CSV·카카오 지오코딩에서 오고 TourAPI 좌표는 관광공사가 찍은
# 대표 지점이라, 같은 장소여도 어긋난다. 특히 해수욕장·공원·궁처럼 넓은 곳은 두 지점이
# 1km 넘게 떨어지기도 한다(예: 광교호수공원 ~994m, 경복궁 ~515m). 이름이 정확히
# 일치해야 여기까지 오므로(pick_photo_match 규칙 2), 동명의 다른 장소는 대개 수십 km
# 떨어진 다른 도시라 2km로 넉넉히 잡아도 오매칭 위험이 거의 없다.
PHOTO_MATCH_DISTANCE_METERS = 2000

# 이름 비교 시 지우는 문자. 괄호·구두점·공백처럼 표기만 다르고 뜻은 같은 것들
# (work_enrichment._TITLE_NOISE_CHARS와 같은 목적).
_NAME_NOISE_CHARS = set(" \t　()[]{}<>「」『』:;,.·・…!?\"'`~-–—/\\")


def normalize_name_for_match(name):
    """이름 비교용으로 정규화한다. 공백·괄호·구두점을 모두 지우고 소문자로 만든다.

    "카페 그루비" 와 "카페그루비", "The Coffee" 와 "the coffee" 를 같은 것으로 본다.
    """
    return "".join(ch for ch in (name or "").casefold() if ch not in _NAME_NOISE_CHARS)


def _title_match_keys(title):
    """TourAPI 제목에서 우리 이름과 비교할 후보들을 정규화해 집합으로 돌려준다.

    TourAPI는 "등명해변(등명해수욕장)"처럼 별칭을 괄호로 붙여 두는 경우가 많다.
    이때 우리 Place 이름은 "등명해변"이거나 "등명해수욕장"일 수 있어서, 제목 전체뿐 아니라
    괄호 앞부분과 괄호 안 내용도 각각 비교 대상으로 둔다.
    """
    title = title or ""
    parts = {title, re.split(r"[(（]", title, maxsplit=1)[0]}
    parts.update(re.findall(r"[(（]([^)）]*)[)）]", title))
    return {key for key in (normalize_name_for_match(p) for p in parts) if key}


def pick_photo_match(place, candidates, *, max_distance_meters=PHOTO_MATCH_DISTANCE_METERS):
    """TourAPI 검색 후보 중 우리 명소와 같은 장소를 하나 고른다. 없으면 None.

    규칙:
      1. 대표 이미지가 없는 후보는 처음부터 제외한다 (사진이 목적이라 의미 없다).
      2. 정규화한 이름이 후보 제목(또는 "제목(별칭)"의 제목·별칭 어느 한쪽)과 정확히
         같아야 한다. 부분 일치·유사도는 인정하지 않는다.
      3. 우리 Place에 좌표가 있으면, 좌표가 있는 후보는 거리가 max_distance_meters 이내여야 한다.
      4. 남은 후보가 여럿이면: 거리가 가까운 것. 좌표로 비교할 수 없는 후보는 맨 뒤로.
      5. 우리 Place에 좌표가 없고, 이름만 같은 후보들의 대표 이미지가 서로 다르면
         어느 게 맞는지 알 수 없으므로 채우지 않는다(None).
    """
    target = normalize_name_for_match(place.name)
    if not target:
        return None

    has_coords = place.latitude is not None and place.longitude is not None

    matched = []
    for candidate in candidates:
        if not candidate.get("first_image"):
            continue
        if target not in _title_match_keys(candidate.get("title")):
            continue

        distance = None
        if has_coords and candidate.get("latitude") is not None and candidate.get("longitude") is not None:
            distance = haversine_distance_meters(
                place.latitude, place.longitude, candidate["latitude"], candidate["longitude"]
            )
            if distance > max_distance_meters:
                continue

        matched.append((distance, candidate))

    if not matched:
        return None

    if not has_coords and len({c["first_image"] for _, c in matched}) > 1:
        return None

    # 좌표로 거리를 잰 후보는 가까운 순, 못 잰 후보(distance=None)는 뒤로.
    matched.sort(key=lambda item: (item[0] is None, item[0] or 0.0))
    return matched[0][1]


def enrich_place_photo(place, *, overwrite=False, max_distance_meters=PHOTO_MATCH_DISTANCE_METERS):
    """Place 하나의 대표 사진을 TourAPI에서 찾아 저장한다.

    이 명소에 TOUR_API PlaceSource가 이미 있으면(한 번 매칭됐거나 관리자가 직접 지정)
    이름 검색·매칭을 건너뛰고 그 content_id로 바로 대표 이미지를 받는다.
    자세한 규칙은 _enrich_place_photo_from 참고.
    """
    return _enrich_place_photo_from(
        place, tour_api, TOUR_API_SOURCE, overwrite=overwrite, max_distance_meters=max_distance_meters
    )


def enrich_place_photo_from_wikimedia(
    place, *, overwrite=False, max_distance_meters=PHOTO_MATCH_DISTANCE_METERS
):
    """Place 하나의 대표 사진을 한국어 위키백과 문서 대표 이미지에서 찾아 저장한다.

    보통 TourAPI(enrich_place_photo)로 못 채운 명소에 이어서 돌린다. 규칙은 같고
    소스만 다르다. 이 명소에 WIKIMEDIA PlaceSource가 이미 있으면 재검색 없이 그
    pageid로 바로 대표 이미지를 받는다. 자세한 규칙은 _enrich_place_photo_from 참고.
    """
    return _enrich_place_photo_from(
        place, wikimedia, WIKIMEDIA_SOURCE, overwrite=overwrite, max_distance_meters=max_distance_meters
    )


def _enrich_place_photo_from(place, source_client, source_name, *, overwrite, max_distance_meters):
    """Place 하나의 대표 사진을 주어진 소스에서 찾아 저장한다.

    source_client는 search_keyword(name) / get_detail(source_id)를 가진 모듈
    (tour_api 또는 wikimedia). source_name은 PlaceSource.source에 남길 값.

    반환: (status, photo_url)
      status:
        "matched"            - 대표 이미지를 새로 채웠다(또는 --overwrite로 바꿨다)
        "matched_no_change"  - 같은 장소는 알지만 이미 같은 값이거나 이미지가 없어 바꿀 게 없었다
        "no_match"           - 이름·좌표가 맞는 관광정보/문서를 못 찾았다
      photo_url: 이번에 저장한 URL (matched일 때만, 아니면 None)

    통신 오류·타임아웃 등 예외는 그대로 올린다 (호출하는 커맨드가 건별로 잡는다).
    """
    known = PlaceSource.objects.filter(place=place, source=source_name).first()
    if known is not None and known.source_id.startswith(NO_MATCH_PREFIX):
        if not overwrite:
            return "no_match", None
        known.delete()  # --overwrite면 실패 기록을 지우고 다시 검색한다
        known = None

    if known is not None:
        detail = source_client.get_detail(known.source_id)
        photo_url = (detail or {}).get("first_image", "")
    else:
        candidates = source_client.search_keyword(place.name)
        match = pick_photo_match(place, candidates, max_distance_meters=max_distance_meters)
        if match is None:
            PlaceSource.objects.get_or_create(
                source=source_name,
                source_id=f"{NO_MATCH_PREFIX}{place.id}",
                defaults={"place": place},
            )
            return "no_match", None
        photo_url = match["first_image"]
        PlaceSource.objects.get_or_create(
            source=source_name, source_id=match["content_id"], defaults={"place": place}
        )

    if not photo_url or place.photo_url == photo_url:
        return "matched_no_change", None
    if place.photo_url and not overwrite:
        return "matched_no_change", None

    place.photo_url = photo_url
    place.save(update_fields=["photo_url"])
    return "matched", photo_url
