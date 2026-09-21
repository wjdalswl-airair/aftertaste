import { useLocaleStore } from '../store/useLocaleStore'
import { publicFetch } from './client'

export type RecommendedSpot = {
  id: number
  name: string
  address: string
  photo_url: string
  // 지금 로그인한 사람이 이 명소를 이미 즐겨찾기 했는지 (BE PlaceSearchSerializer).
  // 비로그인이면 항상 false. 카드 별을 빈 별/채운 별로 맞게 그리는 데 쓴다.
  is_favorited: boolean
}

// 위치 좌표가 있으면 근처 명소, 없으면(권한 거부 등) BE가 랜덤으로 3곳을 준다.
// lang은 항상 붙인다 — 안 보내면 비로그인 사용자는 언어를 바꿔도 명소 콘텐츠가 계속 한국어로 온다 (DETAIL_SPEC 7장).
export function getRecommendedSpots(coords?: { lat: number; lng: number }): Promise<RecommendedSpot[]> {
  const params = new URLSearchParams()
  if (coords) {
    params.set('lat', String(coords.lat))
    params.set('lng', String(coords.lng))
  }
  params.set('lang', useLocaleStore.getState().language)
  return publicFetch<{ places: RecommendedSpot[] }>(`/api/places/recommend/?${params.toString()}`).then(
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
  const lang = useLocaleStore.getState().language
  return publicFetch<PlaceDetail>(`/api/places/${placeId}/?lang=${lang}`)
}

export type MapPlace = {
  id: number
  name: string
  latitude: number
  longitude: number
}

// 지도 탭에서 전체 명소를 마커로 뿌리기 위한 목록. BE에 아직 없는 엔드포인트
// 스펙대로 만들어둔 함수다 (getWorkDetail과 같은 패턴, api/works.ts 참고) —
// BE가 GET /api/places/map/을 구현하면 이 함수는 그대로 동작한다.
// 좌표 필터·페이지네이션 없이 전체를 반환한다(명소 수가 몇 백 개 수준이라 감당 가능,
// BE DETAIL_SPEC 5장 참고, 2026-09-13 사용자 확인).
export function getMapPlaces(): Promise<MapPlace[]> {
  const lang = useLocaleStore.getState().language
  return publicFetch<{ places: MapPlace[] }>(`/api/places/map/?lang=${lang}`).then((res) => res.places)
}

export type TourismCategory = 'food' | 'lodging' | 'experience' | 'history' | 'nature' | 'culture'

export type TourismInfoItem = {
  category: TourismCategory
  name: string
  address: string
  image_url: string
  latitude: number | null
  longitude: number | null
  distance: number | null
  tel: string
}

// 명소 주변 관광정보 (한국관광공사 TourAPI, 이슈 #76). 카카오 주변 상권과 별개이며 번역 없이
// 원본 그대로 온다(lang 파라미터 없음) — DB에 저장 안 하고 매번 실시간으로 받아온다.
// 카테고리 탭 하나만 눌러도 되게, 한 번에 카테고리 1개씩만 요청한다.
export function getTourismInfo(placeId: number, category: TourismCategory): Promise<TourismInfoItem[]> {
  return publicFetch<{ results: TourismInfoItem[] }>(
    `/api/places/${placeId}/tourism-info/?category=${category}`,
  ).then((res) => res.results)
}
