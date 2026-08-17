import math

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
