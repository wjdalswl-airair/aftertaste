import { publicFetch } from './client'

export type RecommendedSpot = {
  id: number
  name: string
  address: string
  photo_url: string
}

// 위치 좌표가 있으면 근처 명소, 없으면(권한 거부 등) BE가 랜덤으로 3곳을 준다.
export function getRecommendedSpots(coords?: { lat: number; lng: number }): Promise<RecommendedSpot[]> {
  const query = coords ? `?lat=${coords.lat}&lng=${coords.lng}` : ''
  return publicFetch<{ places: RecommendedSpot[] }>(`/api/places/recommend/${query}`).then(
    (res) => res.places,
  )
}

export type PlaceDetail = {
  id: number
  name: string
  // 작품 연결 정보. 정확한 필드 구성은 BE 응답으로 확인 필요 (Hero 캡션 표시용, 없어도 화면은 안 깨짐).
  works?: { title?: string; category?: 'drama' | 'movie' }[]
}

// 명예의 전당 리뷰의 명소 id로 이름/작품 정보를 보충할 때만 쓴다 (1건짜리 호출).
export function getPlaceDetail(placeId: number): Promise<PlaceDetail> {
  return publicFetch<PlaceDetail>(`/api/places/${placeId}/`)
}
