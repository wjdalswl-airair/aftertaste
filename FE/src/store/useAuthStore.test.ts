import { beforeEach, describe, expect, it } from 'vitest'
import type { Member } from '../api/auth'
import { useAuthStore } from './useAuthStore'

const member: Member = {
  id: 1,
  email: 'test@example.com',
  nickname: '테스트닉네임',
  profile_image_url: null,
  provider: 'google',
  nationality: null,
  language: null,
  created_at: '2026-01-01T00:00:00Z',
  reviewed_places_count: 0,
  created_courses_count: 0,
}

describe('useAuthStore', () => {
  beforeEach(() => {
    useAuthStore.setState({ member: null, isLoading: true })
  })

  it('초기 상태는 로그인 정보가 없고 로딩 중이다', () => {
    const state = useAuthStore.getState()
    expect(state.member).toBeNull()
    expect(state.isLoading).toBe(true)
  })

  it('setMember로 회원 정보를 저장한다', () => {
    useAuthStore.getState().setMember(member)
    expect(useAuthStore.getState().member).toEqual(member)
  })

  it('setMember(null)로 로그아웃 상태를 만든다', () => {
    useAuthStore.getState().setMember(member)
    useAuthStore.getState().setMember(null)
    expect(useAuthStore.getState().member).toBeNull()
  })

  it('setLoading으로 로딩 상태를 바꾼다', () => {
    useAuthStore.getState().setLoading(false)
    expect(useAuthStore.getState().isLoading).toBe(false)
  })
})
