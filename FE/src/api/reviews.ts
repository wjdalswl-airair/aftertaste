import { authorizedFetch } from './auth'
import { publicFetch } from './client'

export type ReviewPhoto = {
  id: number
  photo_url: string
}

export type ReviewItem = {
  id: number
  place: number
  place_name: string
  place_photo_url: string
  author_nickname: string
  author_profile_image_url: string | null
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

export type ReviewFeedOrdering = 'latest' | 'popular'

export type ReviewFeedPage = {
  count: number
  next: string | null
  previous: string | null
  reviews: ReviewItem[]
}

// 하단 탭 "리뷰"의 전체 피드. 명소 구분 없이 리뷰를 모아 보여준다. 로그인 여부와 상관없이 조회 가능.
// next가 null이 아니면 다음 페이지가 더 있다는 뜻 — FE는 next URL을 그대로 안 쓰고 page 번호를 직접 증가시켜 부른다
// (publicFetch가 항상 BASE_URL을 붙이는 구조라, 서버가 돌려주는 절대 URL을 그대로 넘기면 안 맞는다).
export function getReviewFeed(params: { ordering?: ReviewFeedOrdering; page?: number } = {}): Promise<ReviewFeedPage> {
  const query = new URLSearchParams()
  if (params.ordering) {
    query.set('ordering', params.ordering)
  }
  if (params.page) {
    query.set('page', String(params.page))
  }
  const qs = query.toString()
  return publicFetch<ReviewFeedPage>(`/api/reviews/${qs ? `?${qs}` : ''}`)
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

// 신고 사유는 선택 입력. 같은 사람이 여러 번 신고해도 서버가 1건으로 처리한다(멱등).
export function reportReview(reviewId: number, reason?: string): Promise<void> {
  return authorizedFetch<void>(`/api/reviews/${reviewId}/report/`, {
    method: 'POST',
    body: JSON.stringify({ reason: reason ?? '' }),
  })
}
