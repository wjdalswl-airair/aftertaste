import { auth } from '../lib/firebase'

const BASE_URL = import.meta.env.VITE_API_BASE_URL

// BE의 MemberSerializer 응답 형태 그대로 (BE/accounts/serializers.py)
export type Member = {
  id: number
  email: string
  nickname: string
  profile_image_url: string | null
  provider: 'google' | 'apple'
  nationality: string | null
  language: string | null
  created_at: string
}

type ErrorBody = { detail?: string }

// 로그인이 필요한 API를 호출할 때 공통으로 쓰는 함수.
// Firebase가 가진 idToken을 매번 새로 꺼내서 헤더에 붙인다 (토큰을 직접 저장하지 않음).
async function authorizedFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const idToken = await auth.currentUser?.getIdToken()
  if (!idToken) {
    throw new Error('로그인이 필요합니다')
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const body: ErrorBody | null = await response.json().catch(() => null)
    throw new Error(body?.detail ?? '요청을 처리하지 못했어요')
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

// Firebase idToken으로 로그인한다. 이미 있는 회원이면 그대로 조회되고,
// 처음 온 회원이면 약관 동의(agree_terms)와 함께 가입까지 한 번에 처리된다.
// 로그인 화면에 약관 동의 안내가 항상 보이므로(Figma 기준) 매번 true로 보낸다.
export function loginWithFirebase(): Promise<Member> {
  return authorizedFetch<Member>('/api/account/login/', {
    method: 'POST',
    body: JSON.stringify({ agree_terms: true }),
  })
}

// 내 정보 조회 (BE MeView)
export function getMe(): Promise<Member> {
  return authorizedFetch<Member>('/api/account/', { method: 'GET' })
}
