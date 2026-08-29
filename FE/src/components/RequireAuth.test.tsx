import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import type { Member } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'
import { RequireAuth } from './RequireAuth'

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

function renderWithGuard(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>로그인 화면</div>} />
        <Route element={<RequireAuth />}>
          <Route path="/mypage" element={<div>마이페이지</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireAuth', () => {
  beforeEach(() => {
    useAuthStore.setState({ member: null, isLoading: true })
  })

  it('로그인 상태 확인 중(로딩 중)이면 아무것도 보여주지 않는다', () => {
    useAuthStore.setState({ isLoading: true, member: null })
    const { container } = renderWithGuard('/mypage')
    expect(container).toBeEmptyDOMElement()
  })

  it('비로그인 상태면 로그인 화면으로 보낸다', () => {
    useAuthStore.setState({ isLoading: false, member: null })
    renderWithGuard('/mypage')
    expect(screen.getByText('로그인 화면')).toBeInTheDocument()
    expect(screen.queryByText('마이페이지')).not.toBeInTheDocument()
  })

  it('로그인 상태면 보호된 화면을 그대로 보여준다', () => {
    useAuthStore.setState({ isLoading: false, member })
    renderWithGuard('/mypage')
    expect(screen.getByText('마이페이지')).toBeInTheDocument()
  })
})
