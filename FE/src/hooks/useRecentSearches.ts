import { useState } from 'react'

const STORAGE_KEY = 'recent-searches'
const MAX_COUNT = 10

function readStoredSearches(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as string[]) : []
  } catch {
    return []
  }
}

function writeStoredSearches(searches: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(searches))
}

// 최근 검색어. 로그인 여부와 상관없이 기기(localStorage)에만 저장한다 —
// BE에 로그인 사용자의 검색 기록을 다시 조회하는 API가 없어서 로그인해도 동일하게 처리한다.
export function useRecentSearches() {
  const [recentSearches, setRecentSearches] = useState<string[]>(readStoredSearches)

  function addRecentSearch(keyword: string) {
    const trimmed = keyword.trim()
    if (!trimmed) {
      return
    }
    const next = [trimmed, ...recentSearches.filter((item) => item !== trimmed)].slice(0, MAX_COUNT)
    setRecentSearches(next)
    writeStoredSearches(next)
  }

  function clearRecentSearches() {
    setRecentSearches([])
    writeStoredSearches([])
  }

  return { recentSearches, addRecentSearch, clearRecentSearches }
}
