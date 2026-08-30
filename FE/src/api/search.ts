import { publicFetch } from './client'

export type PlaceSearchResult = {
  id: number
  name: string
  address: string
  photo_url: string
}

export type WorkSearchResult = {
  id: number
  title: string
  category: 'DRAMA' | 'MOVIE'
  poster_url: string
}

export type SearchType = 'WORK' | 'DRAMA' | 'MOVIE'

export type SearchResult = {
  places: PlaceSearchResult[]
  works: WorkSearchResult[]
  message?: string
}

// 통합검색(장소+작품) 또는 구분 조회(type 지정 시 작품만, 그중 드라마/영화만).
// 로그인 상태면 BE가 알아서 검색 기록을 남긴다(FE가 따로 할 일 없음).
export function searchPlaces(keyword: string, type?: SearchType): Promise<SearchResult> {
  const params = new URLSearchParams({ q: keyword })
  if (type) {
    params.set('type', type)
  }
  return publicFetch<SearchResult>(`/api/places/search/?${params.toString()}`)
}

export function getAutocomplete(keyword: string): Promise<string[]> {
  const params = new URLSearchParams({ q: keyword })
  return publicFetch<{ suggestions: string[] }>(`/api/places/search/autocomplete/?${params.toString()}`).then(
    (res) => res.suggestions,
  )
}

// 최근 30일 검색 기록 집계 상위 5개. 로그인 불필요.
export function getPopularKeywords(): Promise<string[]> {
  return publicFetch<{ keywords: string[] }>('/api/search/popular/').then((res) => res.keywords)
}
