import { Home, Map, Route, Star, User } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/useAuthStore'
import { LoginRequiredModal } from './LoginRequiredModal'

// 순서: 홈(큐레이션 진입점) → 지도(명소 찾기) → 코스(주변 코스 둘러보기) → 리뷰(다녀온 뒤 보는 콘텐츠) → 프로필(계정, 관례상 맨 끝).
// 검색은 2026-09-16부터 이 탭이 아니라 메인 페이지 헤더의 검색 아이콘으로 들어간다(MainPage.tsx 참고).
// 프로필 탭만 로그인이 필요하다(App.tsx의 RequireAuth가 /mypage를 감싸고 있음) — requiresAuth로 표시해서
// 비로그인 상태로 누르면 바로 이동시키지 않고 로그인 필요 팝업부터 띄운다.
const TABS = [
  { to: '/', labelKey: 'bottomNav.home', icon: Home, requiresAuth: false },
  { to: '/map', labelKey: 'bottomNav.map', icon: Map, requiresAuth: false },
  { to: '/courses', labelKey: 'bottomNav.course', icon: Route, requiresAuth: false },
  { to: '/reviews', labelKey: 'bottomNav.review', icon: Star, requiresAuth: false },
  { to: '/mypage', labelKey: 'bottomNav.profile', icon: User, requiresAuth: true },
]

type BottomNavProps = {
  // 탭 이동을 그대로 보내지 않고 먼저 확인하고 싶은 화면(예: 작성 중인 폼)에서 넘겨준다.
  // false를 반환하면 이동을 막고(preventDefault), 실제 이동은 호출한 쪽이 알아서 처리한다.
  guardNavigation?: (to: string) => boolean
}

export function BottomNav({ guardNavigation }: BottomNavProps = {}) {
  const { t } = useTranslation()
  const location = useLocation()
  const member = useAuthStore((state) => state.member)
  const [showLoginModal, setShowLoginModal] = useState(false)

  return (
    <>
      {/* nav는 이 안에서 수직 중앙 정렬된다. 흰 띠 배경은 없앴다(2026-09-13 사용자 결정) — 영역 크기는 그대로 둔다. */}
      <div className="fixed inset-x-0 bottom-0 z-30 flex h-22 items-center">
        <nav className="z-40 mx-auto w-full max-w-120 px-4">
          <div className="flex items-center justify-around rounded-2xl bg-white px-5 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.08),0_4px_12px_rgba(0,0,0,0.08)]">
            {TABS.map(({ to, labelKey, icon: Icon, requiresAuth }) => {
              const active = location.pathname === to
              return (
                <Link
                  key={to}
                  to={to}
                  onClick={(event) => {
                    if (requiresAuth && !member) {
                      event.preventDefault()
                      setShowLoginModal(true)
                      return
                    }
                    if (guardNavigation && !guardNavigation(to)) {
                      event.preventDefault()
                    }
                  }}
                  className={`flex flex-col items-center gap-0.5 ${active ? 'text-primary' : 'text-ink-tertiary'}`}
                >
                  <Icon size={20} />
                  <span className="text-[10px]">{t(labelKey)}</span>
                </Link>
              )
            })}
          </div>
        </nav>
      </div>

      {showLoginModal && <LoginRequiredModal onClose={() => setShowLoginModal(false)} />}
    </>
  )
}
