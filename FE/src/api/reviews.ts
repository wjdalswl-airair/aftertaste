import { authorizedFetch } from './auth'
import { publicFetch } from './client'

export type ReviewPhoto = {
  id: number
  photo_url: string
}

export type ReviewItem = {
  id: number
  place: number
  author_nickname: string
  rating: number
  content: string
  language: string
  photos: ReviewPhoto[]
  like_count: number
  is_liked_by_me: boolean
  created_at: string
  updated_at: string
}

export type ReviewInput = {
  rating: number
  content: string
  language: string
  photo_urls: string[]
}

// 명소 리뷰 목록. 로그인 여부와 상관없이 조회 가능.
export function getPlaceReviews(placeId: number): Promise<ReviewItem[]> {
  return publicFetch<{ reviews: ReviewItem[] }>(`/api/places/${placeId}/reviews/`).then((res) => res.reviews)
}

// 내가 쓴 리뷰 모아보기 (마이페이지). place는 ID로만 온다(장소명·썸네일 없음).
export function getMyReviews(): Promise<ReviewItem[]> {
  return authorizedFetch<{ reviews: ReviewItem[] }>('/api/account/reviews/').then((res) => res.reviews)
}

export function createReview(placeId: number, input: ReviewInput): Promise<{ reviewId: number }> {
  return authorizedFetch<{ reviewId: number }>(`/api/places/${placeId}/reviews/`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function updateReview(reviewId: number, input: ReviewInput): Promise<void> {
  return authorizedFetch<void>(`/api/reviews/${reviewId}/`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

// 이미 지워진 리뷰를 또 지워도 BE가 조용히 성공(204) 처리한다.
export function deleteReview(reviewId: number): Promise<void> {
  return authorizedFetch<void>(`/api/reviews/${reviewId}/`, { method: 'DELETE' })
}

export function likeReview(reviewId: number): Promise<void> {
  return authorizedFetch<void>(`/api/reviews/${reviewId}/like/`, { method: 'POST' })
}

export function unlikeReview(reviewId: number): Promise<void> {
  return authorizedFetch<void>(`/api/reviews/${reviewId}/like/`, { method: 'DELETE' })
}
