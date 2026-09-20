import { LogIn, Search } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { BottomNav } from '../components/BottomNav'
import { Hero } from '../components/Hero'
import { LanguageSheet } from '../components/LanguageSheet'
import { LocationPermissionModal } from '../components/LocationPermissionModal'
import { RecommendedSpots } from '../components/RecommendedSpots'
import { RegionalTopPlacesCarousel } from '../components/RegionalTopPlacesCarousel'
import { TopPlacesCarousel } from '../components/TopPlacesCarousel'
import { WeatherWidget } from '../components/WeatherWidget'
import { useGeolocation } from '../hooks/useGeolocation'
import { useAuthStore } from '../store/useAuthStore'

export function MainPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const member = useAuthStore((state) => state.member)
  const isLoading = useAuthStore((state) => state.isLoading)
  // 메인 화면에서 위치가 필요한 위젯(추천 명소, 날씨)이 각자 useGeolocation을 부르면
  // 동의 모달이 중복으로 뜰 수 있어서, 이 화면이 하나만 소유하고 아래로 내려준다
  // (2026-09-20, 날씨 위젯 추가하며 리팩터).
  const { status, coords, showConsentModal, handleAllow, handleDeny } = useGeolocation()

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="flex items-center justify-between px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <div className="flex items-center gap-4">
          <LanguageSheet />
          {!isLoading && !member && (
            <Link to="/login" aria-label="로그인">
              <LogIn size={22} className="text-ink" />
            </Link>
          )}
        </div>
      </header>

      <div className="flex flex-col gap-2 px-4">
        <div className="flex justify-end">
          <WeatherWidget status={status} coords={coords} />
        </div>

        <div className="flex items-center gap-2 rounded-lg bg-accent/15 p-4">
          <Search size={16} className="text-ink-tertiary" />
          <input
            type="text"
            onFocus={() => navigate('/search')}
            placeholder={t('searchPage.placeholder')}
            className="flex-1 bg-transparent text-sm text-ink placeholder:text-ink-tertiary outline-none"
          />
        </div>
      </div>

      <div className="px-4">
        <h1 className="text-xl font-bold text-ink">
          {t('mainPage.greeting.hello')}
          {!isLoading && member && t('mainPage.greeting.nameSuffix', { name: member.nickname })}
        </h1>
        <p className=" text-ink-secondary">{t('mainPage.greeting.subtitle')}</p>
      </div>

      <Hero />
      <RecommendedSpots status={status} coords={coords} />
      <TopPlacesCarousel />
      <RegionalTopPlacesCarousel />

      {showConsentModal && <LocationPermissionModal onAllow={handleAllow} onDeny={handleDeny} />}

      <BottomNav />
    </main>
  )
}
