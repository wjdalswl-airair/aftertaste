import { LogIn } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { BottomNav } from '../components/BottomNav'
import { Hero } from '../components/Hero'
import { LanguageSheet } from '../components/LanguageSheet'
import { RecommendedSpots } from '../components/RecommendedSpots'
import { TopPlacesCarousel } from '../components/TopPlacesCarousel'
import { useAuthStore } from '../store/useAuthStore'

export function MainPage() {
  const { t } = useTranslation()
  const member = useAuthStore((state) => state.member)
  const isLoading = useAuthStore((state) => state.isLoading)

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="flex items-center justify-between px-4 pt-6">
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

      <div className="px-4">
        <h1 className="text-xl font-bold text-ink">
          {t('mainPage.greeting.hello')}
          {!isLoading && member && t('mainPage.greeting.nameSuffix', { name: member.nickname })}
        </h1>
        <p className=" text-ink-secondary">{t('mainPage.greeting.subtitle')}</p>
      </div>

      <Hero />
      <RecommendedSpots />
      <TopPlacesCarousel />

      <BottomNav />
    </main>
  )
}
