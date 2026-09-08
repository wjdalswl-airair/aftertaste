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

export function getHallOfFame(): Promise<HallOfFameReview | null> {
  return publicFetch<{ review: HallOfFameReview | null }>('/api/main/hall-of-fame/').then(
    (res) => res.review,
  )
}

export function getTopPlaces(): Promise<TopPlace[]> {
  return publicFetch<{ places: TopPlace[] }>('/api/main/top-places/').then((res) => res.places)
}
