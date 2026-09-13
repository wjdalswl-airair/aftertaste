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
}

// GET /api/works/{id}/ (BE places/views.py:WorkDetailView, feature/be/work_detail_expand에서 구현 완료).
export function getWorkDetail(workId: number): Promise<WorkDetail> {
  const lang = useLocaleStore.getState().language
  return publicFetch<WorkDetail>(`/api/works/${workId}/?lang=${lang}`)
}
