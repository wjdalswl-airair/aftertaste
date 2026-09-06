import { Home, Search, User } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useLocation } from 'react-router-dom'

const TABS = [
  { to: '/', labelKey: 'bottomNav.home', icon: Home },
  { to: '/search', labelKey: 'bottomNav.search', icon: Search },
  { to: '/mypage', labelKey: 'bottomNav.profile', icon: User },
]

export function BottomNav() {
  const { t } = useTranslation()
  const location = useLocation()

  return (
    <>
      {/* 플로팅 탭 뒤로 페이지 내용이 비치지 않도록 화면 하단을 흰색으로 깔아준다. nav는 이 안에서 수직 중앙 정렬된다 */}
      <div className="fixed inset-x-0 bottom-0 z-30 flex h-22 items-center bg-white">
        <nav className="z-40 mx-auto w-full max-w-120 px-4">
          <div className="flex items-center justify-around rounded-2xl bg-white/95 px-5 py-3 shadow-[0_-4px_12px_rgba(0,0,0,0.08),0_4px_12px_rgba(0,0,0,0.08)]">
            {TABS.map(({ to, labelKey, icon: Icon }) => {
              const active = location.pathname === to
              return (
                <Link
                  key={to}
                  to={to}
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
    </>
  )
}
