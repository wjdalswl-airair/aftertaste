import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

// 페이지 이동마다 스크롤을 맨 위로 올린다. React Router는 SPA 라우팅이라 브라우저가
// 스크롤 위치를 자동으로 초기화 안 해줘서, 안 넣으면 이전 화면에서 스크롤한 위치가
// 다음 화면에도 그대로 남는다.
export function ScrollToTop() {
  const { pathname } = useLocation()

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])

  return null
}
