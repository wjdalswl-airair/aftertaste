import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Member } from './auth'

// vi.mock은 파일 최상단으로 끌어올려지므로, 그 안에서 쓸 값은 vi.hoisted로 만든다.
const { mockAuth, getIdToken, signOutMock } = vi.hoisted(() => {
  const getIdToken = vi.fn()
  const signOutMock = vi.fn()
  return {
    mockAuth: { currentUser: null as null | { getIdToken: typeof getIdToken } },
    getIdToken,
    signOutMock,
  }
})

vi.mock('../lib/firebase', () => ({
  auth: mockAuth,
}))

vi.mock('firebase/auth', () => ({
  signOut: signOutMock,
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
  reviewed_places_count: 3,
  created_courses_count: 2,
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

  it('updateProfile은 PATCH로 프로필을 수정한다', async () => {
    const { updateProfile } = await import('./auth')
    getIdToken.mockResolvedValue('fake-id-token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

    await updateProfile({ nickname: '새닉네임' })

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/account/'),
      expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ nickname: '새닉네임' }) }),
    )
  })

  it('updateProfile은 닉네임 길이 초과 시 서버 에러 메시지를 던진다', async () => {
    const { updateProfile } = await import('./auth')
    getIdToken.mockResolvedValue('fake-id-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: false, status: 400, json: async () => ({ detail: '닉네임이 너무 길어요' }) }),
    )

    await expect(updateProfile({ nickname: '아주아주아주아주아주아주아주긴닉네임' })).rejects.toThrow(
      '닉네임이 너무 길어요',
    )
  })

  it('deleteAccount는 DELETE로 탈퇴 처리한다', async () => {
    const { deleteAccount } = await import('./auth')
    getIdToken.mockResolvedValue('fake-id-token')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

    await deleteAccount()

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/account/'),
      expect.objectContaining({ method: 'DELETE' }),
    )
  })

  it('logout은 firebase signOut을 호출한다', async () => {
    const { logout } = await import('./auth')
    signOutMock.mockResolvedValue(undefined)

    await logout()

    expect(signOutMock).toHaveBeenCalledWith(mockAuth)
  })

  it('kakaoLogin은 인가 코드로 Firebase 커스텀 토큰을 요청한다(로그인 전이라 idToken 없이 호출)', async () => {
    const { kakaoLogin } = await import('./auth')
    mockAuth.currentUser = null
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ firebase_custom_token: 'fake-custom-token' }),
      }),
    )

    const result = await kakaoLogin('fake-code', 'https://example.com/login')

    expect(result).toEqual({ firebase_custom_token: 'fake-custom-token' })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/account/kakao/token/'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ code: 'fake-code', redirect_uri: 'https://example.com/login' }),
      }),
    )
  })

  it('kakaoLogin이 실패하면 에러를 던진다', async () => {
    const { kakaoLogin } = await import('./auth')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: '다시 로그인하세요' }),
      }),
    )

    await expect(kakaoLogin('bad-code', 'https://example.com/login')).rejects.toThrow('다시 로그인하세요')
  })
})
