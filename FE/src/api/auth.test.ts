import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Member } from './auth'

// vi.mock은 파일 최상단으로 끌어올려지므로, 그 안에서 쓸 값은 vi.hoisted로 만든다.
const { mockAuth, getIdToken } = vi.hoisted(() => {
  const getIdToken = vi.fn()
  return {
    mockAuth: { currentUser: null as null | { getIdToken: typeof getIdToken } },
    getIdToken,
  }
})

vi.mock('../lib/firebase', () => ({
  auth: mockAuth,
}))

const member: Member = {
  id: 1,
  email: 'test@example.com',
  nickname: '테스트닉네임',
  profile_image_url: null,
  provider: 'google',
  nationality: null,
  language: null,
  created_at: '2026-01-01T00:00:00Z',
}

describe('src/api/auth.ts', () => {
  beforeEach(() => {
    mockAuth.currentUser = { getIdToken }
    getIdToken.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('로그인 성공 시 서버가 준 회원 정보를 반환한다', async () => {
    const { loginWithFirebase } = await import('./auth')
    getIdToken.mockResolvedValue('fake-id-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => member,
      }),
    )

    const result = await loginWithFirebase()

    expect(result).toEqual(member)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/account/login/'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ agree_terms: true }),
        headers: expect.objectContaining({ Authorization: 'Bearer fake-id-token' }),
      }),
    )
  })

  it('Firebase 로그인이 안 되어 있으면(idToken 없음) 요청 없이 에러를 던진다', async () => {
    const { loginWithFirebase } = await import('./auth')
    mockAuth.currentUser = null
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)

    await expect(loginWithFirebase()).rejects.toThrow('로그인이 필요합니다')
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('서버가 실패 응답을 주면 응답의 detail 메시지로 에러를 던진다', async () => {
    const { loginWithFirebase } = await import('./auth')
    getIdToken.mockResolvedValue('fake-id-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: '약관 동의가 필요합니다' }),
      }),
    )

    await expect(loginWithFirebase()).rejects.toThrow('약관 동의가 필요합니다')
  })

  it('getMe는 GET으로 내 정보를 조회한다', async () => {
    const { getMe } = await import('./auth')
    getIdToken.mockResolvedValue('fake-id-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => member,
      }),
    )

    const result = await getMe()

    expect(result).toEqual(member)
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/account/'),
      expect.objectContaining({ method: 'GET' }),
    )
  })
})
