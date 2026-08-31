import { signOut } from 'firebase/auth'
import { auth } from '../lib/firebase'
import { publicFetch } from './client'

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
  // 마이페이지 프로필 요약 (BE MemberSerializer 참고)
  reviewed_places_count: number
  created_courses_count: number
}

type ErrorBody = { detail?: string }

// 로그인이 필요한 API를 호출할 때 공통으로 쓰는 함수.
// Firebase가 가진 idToken을 매번 새로 꺼내서 헤더에 붙인다 (토큰을 직접 저장하지 않음).
export async function authorizedFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
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

// 프로필(닉네임·프로필 사진) 수정. 보낸 값만 반영된다 (BE MeView.patch, 204).
export function updateProfile(payload: {
  nickname?: string
  profile_image_url?: string | null
}): Promise<void> {
  return authorizedFetch<void>('/api/account/', { method: 'PATCH', body: JSON.stringify(payload) })
}

// 회원 탈퇴 (BE MeView.delete, 204). 성공하면 호출부에서 logout()까지 이어서 호출한다.
export function deleteAccount(): Promise<void> {
  return authorizedFetch<void>('/api/account/', { method: 'DELETE' })
}

// 로그아웃. Firebase 세션을 지우면 useInitAuth의 onAuthStateChanged가 감지해서
// useAuthStore의 member를 알아서 null로 정리해준다.
export function logout(): Promise<void> {
  return signOut(auth)
}

// 국적/언어 저장. 로그인 여부와 관계없이 부를 수 있다.
// 로그인 상태면 서버가 실제로 저장하고, 비로그인이면 값만 검증해서 그대로 돌려준다
// (비로그인 저장은 프론트가 localStorage로 직접 한다 — useLocaleStore).
export function updateLocale(payload: {
  nationality?: string
  language?: string
}): Promise<{ language: string | null }> {
  return publicFetch<{ language: string | null }>('/api/account/locale/', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
