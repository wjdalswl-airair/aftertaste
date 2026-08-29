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
