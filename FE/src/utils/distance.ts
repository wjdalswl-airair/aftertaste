const EARTH_RADIUS_KM = 6371

// 두 좌표 사이의 직선 거리(km)를 haversine 공식으로 계산한다.
// 코스 후보 장소들의 거리 표시용(Figma 목업엔 있으나 BE 응답엔 없는 값).
export function getDistanceKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return EARTH_RADIUS_KM * c
}
