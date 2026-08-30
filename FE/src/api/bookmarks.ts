import { authorizedFetch } from './auth'

// 즐겨찾기는 로그인이 필요한 기능이다. 안 한 상태로 부르면 authorizedFetch가 에러를 던진다.
export function addFavorite(placeId: number): Promise<void> {
  return authorizedFetch<void>(`/api/places/${placeId}/favorite/`, { method: 'POST' })
}

export function removeFavorite(placeId: number): Promise<void> {
  return authorizedFetch<void>(`/api/places/${placeId}/favorite/`, { method: 'DELETE' })
}
