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
