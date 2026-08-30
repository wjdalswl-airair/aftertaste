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

export type WorkInfo = {
  id: number
  title: string
  description: string
  category: 'DRAMA' | 'MOVIE'
  release_date: string | null
  main_cast: string
  director: string
  poster_url: string
}

// 명소에 연결된 작품 하나 + 이 명소가 그 작품에서 나온 장면 설명.
export type PlaceWork = {
  work: WorkInfo
  scene_description: string
}

export type NearbyPlace = {
  place_name: string | null
  address_name: string | null
  road_address_name: string | null
  latitude: number
  longitude: number
  category_name: string | null
}

export type PlaceReviewPhoto = {
  id: number
  photo_url: string
}

export type PlaceReview = {
  id: number
  place: number
  author_nickname: string
  rating: number
  content: string
  language: string
  photos: PlaceReviewPhoto[]
  like_count: number
  is_liked_by_me: boolean
  created_at: string
  updated_at: string
}

export type PlaceDetail = {
  id: number
  name: string
  address: string
  photo_url: string
  business_hours: string
  recommended_time: string
  photo_tips: string
  etiquette: string
  description: string
  // Place 모델의 DecimalField라 DRF가 정밀도 보존을 위해 문자열로 내려준다 (실제 API 응답으로 확인함).
  latitude: string | null
  longitude: string | null
  works: PlaceWork[]
  nearby_places: NearbyPlace[]
  is_favorited: boolean
  reviews: PlaceReview[]
  review_average_rating: number | null
  review_count: number
}

// 명소 상세 (명소 정보 + 등장 작품 + 주변 상권 + 리뷰를 한 번에 받는다).
// Hero의 명예의 전당 캡션 보충용으로도 재사용한다 (1건짜리 호출, 없어도 화면은 안 깨짐).
export function getPlaceDetail(placeId: number): Promise<PlaceDetail> {
  return publicFetch<PlaceDetail>(`/api/places/${placeId}/`)
}
