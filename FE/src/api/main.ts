import { useLocaleStore } from '../store/useLocaleStore'
import { publicFetch } from './client'

export type Banner = {
  id: number
  image_url: string
  link_url: string
  order: number
}

export type HallOfFameReview = {
  id: number
  place: number
  author_nickname: string
  rating: number
  content: string
  language: string
  photos: { id: number; photo_url: string }[]
  like_count: number
  is_liked_by_me: boolean
  created_at: string
  updated_at: string
}

export type HallOfFameWork = {
  title: string
  category: 'DRAMA' | 'MOVIE'
}

// 명예의전당 카드 캡션에 필요한 최소 명소 정보. 상세 API(PlaceDetail)와 달리 이름 +
// 대표 작품 하나만 있다 — 히어로 캡션 한 줄 때문에 무거운 명소 상세 API를 또 부르지
// 않으려고 BE가 hall-of-fame 응답에 바로 얹어준다.
export type HallOfFamePlace = {
  id: number
  name: string
  work: HallOfFameWork | null
}

export type TopPlace = {
  id: number
  name: string
  address: string
  photo_url: string
  favorite_count: number
  // 지금 로그인한 사람이 이 명소를 이미 즐겨찾기 했는지 (BE TopPlaceSerializer).
  // 비로그인이면 항상 false. 카드 별을 빈 별/채운 별로 맞게 그리는 데 쓴다.
  is_favorited: boolean
}

export function getBanners(): Promise<Banner[]> {
  return publicFetch<{ banners: Banner[] }>('/api/banners/').then((res) => res.banners)
}

// lang은 항상 붙인다 — 안 보내면 비로그인 사용자는 언어를 바꿔도 place 캡션이 계속 한국어로 온다
// (getRecommendedSpots·getPlaceDetail과 같은 이유, DETAIL_SPEC 7장).
export function getHallOfFame(): Promise<{ review: HallOfFameReview; place: HallOfFamePlace | null } | null> {
  const lang = useLocaleStore.getState().language
  return publicFetch<{ review: HallOfFameReview | null; place: HallOfFamePlace | null }>(
    `/api/main/hall-of-fame/?lang=${lang}`,
  ).then((res) => (res.review ? { review: res.review, place: res.place } : null))
}

export function getTopPlaces(): Promise<TopPlace[]> {
  return publicFetch<{ places: TopPlace[] }>('/api/main/top-places/').then((res) => res.places)
}
