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

// BE에 아직 없는 엔드포인트 스펙대로 만들어둔 함수. BE가 GET /api/works/{id}/를
// 구현하면 이 함수는 그대로 동작한다 (2026-08-30, 사용자 확인 후 API 스펙만 먼저 정리해 전달).
export function getWorkDetail(workId: number): Promise<WorkDetail> {
  return publicFetch<WorkDetail>(`/api/works/${workId}/`)
}
