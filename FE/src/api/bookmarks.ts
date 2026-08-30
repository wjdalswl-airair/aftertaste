import { authorizedFetch } from './auth'
import type { RecommendedSpot } from './spots'

// 즐겨찾기는 로그인이 필요한 기능이다. 안 한 상태로 부르면 authorizedFetch가 에러를 던진다.
export function addFavorite(placeId: number): Promise<void> {
  return authorizedFetch<void>(`/api/places/${placeId}/favorite/`, { method: 'POST' })
}

export function removeFavorite(placeId: number): Promise<void> {
  return authorizedFetch<void>(`/api/places/${placeId}/favorite/`, { method: 'DELETE' })
}

export type Favorite = {
  id: number
  // 명소뿐 아니라 코스도 즐겨찾기할 수 있어서 BE가 둘을 같이 내려주지만, 이번 Phase는
  // 명소만 다룬다 (코스는 Phase8). type === 'COURSE'면 place는 null이다.
  type: 'PLACE' | 'COURSE'
  place: RecommendedSpot | null
  created_at: string
}

export function getMyFavorites(): Promise<Favorite[]> {
  return authorizedFetch<{ favorites: Favorite[] }>('/api/account/favorites/').then((res) => res.favorites)
}
