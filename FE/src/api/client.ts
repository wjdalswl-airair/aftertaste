import { auth } from '../lib/firebase'

const BASE_URL = import.meta.env.VITE_API_BASE_URL

type ErrorBody = { detail?: string }

// 로그인이 "선택"인 API를 부를 때 쓰는 공용 함수.
// Firebase에 로그인돼 있으면 토큰을 붙이고, 아니어도 에러 없이 그대로 요청한다.
export async function publicFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const idToken = await auth.currentUser?.getIdToken()

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
    'Content-Type': 'application/json',
  }
  if (idToken) {
    headers.Authorization = `Bearer ${idToken}`
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })

  if (!response.ok) {
    const body: ErrorBody | null = await response.json().catch(() => null)
    throw new Error(body?.detail ?? '요청을 처리하지 못했어요')
  }

  if (response.status === 204) {
    return undefined as T
  }

  try {
    return (await response.json()) as T
  } catch {
    // authorizedFetch와 같은 이유 — 200/201인데 본문이 빈 응답을 실패로 오인하지 않는다.
    return undefined as T
  }
}
