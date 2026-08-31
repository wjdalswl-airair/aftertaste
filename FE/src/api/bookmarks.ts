import { authorizedFetch } from './auth'
import type { Course } from './courses'
import type { RecommendedSpot } from './spots'

// 즐겨찾기는 로그인이 필요한 기능이다. 안 한 상태로 부르면 authorizedFetch가 에러를 던진다.
export function addFavorite(placeId: number): Promise<void> {
  return authorizedFetch<void>(`/api/places/${placeId}/favorite/`, { method: 'POST' })
}

export function removeFavorite(placeId: number): Promise<void> {
  return authorizedFetch<void>(`/api/places/${placeId}/favorite/`, { method: 'DELETE' })
}

export function addCourseFavorite(courseId: number): Promise<void> {
  return authorizedFetch<void>(`/api/courses/${courseId}/favorite/`, { method: 'POST' })
}

export function removeCourseFavorite(courseId: number): Promise<void> {
  return authorizedFetch<void>(`/api/courses/${courseId}/favorite/`, { method: 'DELETE' })
}

export type Favorite = {
  id: number
  // 명소·코스 즐겨찾기가 한 응답에 섞여서 온다. type === 'PLACE'면 course는 null,
  // type === 'COURSE'면 place는 null이다 (BE FavoriteSerializer).
  type: 'PLACE' | 'COURSE'
  place: RecommendedSpot | null
  course: Course | null
  created_at: string
}

export function getMyFavorites(): Promise<Favorite[]> {
  return authorizedFetch<{ favorites: Favorite[] }>('/api/account/favorites/').then((res) => res.favorites)
}
