import math
from decimal import Decimal, InvalidOperation

from django.db import transaction

# 서로 다른 출처의 명소가 이 거리(미터) 이내면 같은 물리적 장소로 본다.
SAME_PLACE_DISTANCE_METERS = 100

_EARTH_RADIUS_METERS = 6371000


def haversine_distance_meters(lat1, lng1, lat2, lng2):
    """두 좌표 사이의 거리를 미터 단위로 계산한다 (지구를 구로 근사).

    latitude/longitude는 Decimal(Place 필드)이나 float(외부 API 응답) 둘 다 들어올 수 있다.
    """
    lat1, lng1, lat2, lng2 = (math.radians(float(v)) for v in (lat1, lng1, lat2, lng2))

    d_lat = lat2 - lat1
    d_lng = lng2 - lng1
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return _EARTH_RADIUS_METERS * c


def to_decimal(value):
    """값을 Decimal로 바꾼다. (바뀐 값, 성공 여부)를 돌려준다.

    값이 없으면(None/빈 문자열) 성공으로 치고 None을 돌려준다.
    "-", "정보없음"처럼 값은 있는데 숫자가 아니면 실패로 치고 None을 돌려준다.
    """
    if value is None or value == "":
        return None, True
    try:
        return Decimal(str(value)), True
    except InvalidOperation:
        return None, False


# KCISA CSV의 미디어타입 → Work.category. 우리 서비스는 영화·드라마 촬영지라
# drama/movie만 다루고, 나머지(show=예능, artist=뮤직비디오 등)는 아예 가져오지 않는다.
_MEDIA_TYPE_TO_CATEGORY = {"drama": "DRAMA", "movie": "MOVIE"}

# Work.title은 CharField(max_length=200)이라 넘으면 저장이 실패한다. 잘라서 저장한다
# (translation.py의 NAME_TITLE_MAX_LENGTH 처리와 같은 방식).
_WORK_TITLE_MAX_LENGTH = 200


def media_type_to_category(media_type):
    """KCISA 미디어타입 문자열을 Work.category 값으로 바꾼다.

    drama/movie가 아니면(예능·뮤직비디오·빈값 등) None. import 커맨드가 이 값으로
    "가져올 행인지"를 판단하고, link_place_to_work가 같은 기준으로 작품을 잇는다.
    """
    return _MEDIA_TYPE_TO_CATEGORY.get((media_type or "").strip().lower())


def link_place_to_work(place, *, title, media_type):
    """촬영지(place)를 그 작품(Work)에 잇는다. 영화·드라마 촬영지에만 적용된다.

    - media_type이 drama/movie가 아니거나 title이 비어 있으면 아무것도 안 하고 None을 돌려준다.
    - 공백을 정리한 제목 문자열이 같으면 같은 작품으로 본다 — KCISA CSV엔 작품을 구분할
      다른 키(연도·작품ID)가 없고, 같은 드라마는 늘 같은 제목으로 적혀 있어 이걸로 충분하다.
      서로 다른 출처(경기 데이터 드림 등) 사이의 표기 차이 병합은 별도 작업이다 (DETAIL_SPEC 7장 #1).
    - 이미 이어진 place-work면 아무것도 바꾸지 않는다(get_or_create만). scene_description(장면
      설명)은 관리자가 채우는 값이라 재수집으로 덮어쓰지 않는다 — business_hours 보존과 같은 원칙.

    반환값: (work, linked) — work는 이어진 Work(대상이 아니면 None),
            linked는 이번에 place-work 연결이 새로 생겼는지 여부.
    """
    from places.models import PlaceWork, Work

    category = media_type_to_category(media_type)
    if category is None:
        return None, False

    normalized_title = " ".join((title or "").split())[:_WORK_TITLE_MAX_LENGTH]
    if not normalized_title:
        return None, False

    work, _ = Work.objects.get_or_create(title=normalized_title, category=category)
    _, linked = PlaceWork.objects.get_or_create(place=place, work=work)
    return work, linked


def build_composite_source_id(*parts, delimiter="|"):
    """원본에 고유번호가 없는 출처를 위해, 여러 필드를 하나의 source_id 문자열로 합친다.

    None은 빈 문자열로 취급한다. 같은 조합이면 항상 같은 문자열이 나와야 재수집 때
    중복 없이 같은 PlaceSource를 찾을 수 있다.
    """
    return delimiter.join(str(part) if part is not None else "" for part in parts)


_DEGREE_BUFFER = Decimal("0.0015")  # 위경도 1도가 대략 111km이므로, 100m보다 넉넉한 여유폭


def find_nearby_place(latitude, longitude):
    """좌표가 SAME_PLACE_DISTANCE_METERS 이내인 기존 Place 중 가장 가까운 것을 찾는다.

    좌표가 없으면 None. 여러 개가 거리 안에 있으면 가장 가까운 것 하나를 고른다.

    명소 전체를 매번 파이썬으로 순회하면 명소 수가 만 단위로 늘 때 감당할 수 없이 느려진다
    (실제 한국문화정보원 CSV만 15,000여 건). 그래서 DB에서 위경도 범위로 후보를 먼저 크게
    좁힌 뒤(_DEGREE_BUFFER), 그 소수의 후보에 대해서만 정확한 거리를 계산한다.
    """
    from places.models import Place

    if latitude is None or longitude is None:
        return None

    latitude = Decimal(str(latitude))
    longitude = Decimal(str(longitude))
    candidates = Place.objects.filter(
        latitude__range=(latitude - _DEGREE_BUFFER, latitude + _DEGREE_BUFFER),
        longitude__range=(longitude - _DEGREE_BUFFER, longitude + _DEGREE_BUFFER),
    )

    nearest_place = None
    nearest_distance = None
    for place in candidates:
        distance = haversine_distance_meters(latitude, longitude, place.latitude, place.longitude)
        if distance <= SAME_PLACE_DISTANCE_METERS and (nearest_distance is None or distance < nearest_distance):
            nearest_place, nearest_distance = place, distance
    return nearest_place


def save_place_from_source(source, source_id, *, name="", address="", latitude=None, longitude=None,
                            create_only_fields=None):
    """공공데이터 한 건을 Place/PlaceSource에 저장한다 (docs/DETAIL_SPEC.md 3-6절 가져오기 규칙).

    1. (source, source_id)로 이미 아는 PlaceSource가 있으면, 그 명소의 공공데이터 필드
       (name/address/latitude/longitude)를 새 값이 비어있지 않은 것만 갱신한다.
    2. 없고 좌표가 있으면, 100m 이내 기존 명소를 찾아 PlaceSource만 새로 붙인다.
       이 경로에서는 기존 명소의 어떤 필드도 덮어쓰지 않는다 — 여러 출처 값이 겹칠 때
       뭘 우선할지는 아직 안 정해졌고(별도 결정 예정), 정해지기 전까지는 아무것도
       건드리지 않는 쪽이 안전하다.
    3. 그래도 없으면 새 명소 + PlaceSource를 만든다. 이때만 create_only_fields(예:
       {"business_hours": "..."})를 값이 비어있지 않은 것만 적용한다 — 관리자 전용 필드에
       공공데이터로 시작값만 채워주고, 그 뒤로는 관리자가 고친 값을 지키기 위해서다.

    반환값: (place, created: bool, matched_by: "source_id" | "distance" | "new")
    """
    from places.models import Place, PlaceSource

    create_only_fields = create_only_fields or {}

    place_source = PlaceSource.objects.select_related("place").filter(source=source, source_id=source_id).first()
    if place_source is not None:
        place = place_source.place
        changed = False
        for field_name, value in (("name", name), ("address", address), ("latitude", latitude),
                                   ("longitude", longitude)):
            if value in (None, ""):
                continue
            setattr(place, field_name, value)
            changed = True
        if changed:
            place.save()
        return place, False, "source_id"

    nearby_place = find_nearby_place(latitude, longitude)
    if nearby_place is not None:
        PlaceSource.objects.create(place=nearby_place, source=source, source_id=source_id)
        return nearby_place, False, "distance"

    with transaction.atomic():
        place = Place.objects.create(name=name, address=address, latitude=latitude, longitude=longitude)
        has_create_only_values = False
        for field_name, value in create_only_fields.items():
            if value not in (None, ""):
                setattr(place, field_name, value)
                has_create_only_values = True
        if has_create_only_values:
            place.save()
        PlaceSource.objects.create(place=place, source=source, source_id=source_id)
    return place, True, "new"
