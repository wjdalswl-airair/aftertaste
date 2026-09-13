import { useLocaleStore } from '../store/useLocaleStore'
import { publicFetch } from './client'

export type WorkPlace = {
  id: number
  name: string
  address: string
  photo_url: string
}

export type WorkDetail = {
  id: number
  title: string
  description: string
  category: 'DRAMA' | 'MOVIE'
  release_date: string | null
  main_cast: string
  director: string
  poster_url: string
  places: WorkPlace[]
  // 작품 상세정보 4개 필드 추가(issue #59). rating은 DRF DecimalField 기본 동작대로 문자열로 온다
  // (예: "8.5") — 소수점을 그대로 보여줘야 해서 숫자로 바꾸지 않고 문자열 그대로 쓴다.
  rating: string | null
  runtime: number | null
  genre: string
}

// GET /api/works/{id}/ (BE places/views.py:WorkDetailView, feature/be/work_detail_expand에서 구현 완료).
export function getWorkDetail(workId: number): Promise<WorkDetail> {
  const lang = useLocaleStore.getState().language
  return publicFetch<WorkDetail>(`/api/works/${workId}/?lang=${lang}`)
}
