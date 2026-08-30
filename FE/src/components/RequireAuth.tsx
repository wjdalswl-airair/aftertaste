import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'

// 로그인이 필요한 화면들을 감싸는 공통 가드.
// 비로그인 상태면 "로그인이 필요한 기능입니다"와 함께 로그인 화면으로 보낸다.
export function RequireAuth() {
  const member = useAuthStore((state) => state.member)
  const isLoading = useAuthStore((state) => state.isLoading)
  const location = useLocation()

  if (isLoading) {
    return null
  }

  if (!member) {
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname, message: '로그인이 필요한 기능입니다' }}
        replace
      />
    )
  }

  return <Outlet />
}
