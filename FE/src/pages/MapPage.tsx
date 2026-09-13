import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { BottomNav } from '../components/BottomNav'
import { LanguageSheet } from '../components/LanguageSheet'

// 전체 명소를 카카오맵에 표시하는 화면 (자리만 먼저 만들어둠). 실제 지도 연동은 별도 작업.
export function MapPage() {
  const { t } = useTranslation()

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="flex items-center justify-between px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <LanguageSheet />
      </header>

      <div className="px-4">
        <h1 className="text-xl font-bold text-ink">{t('mapPage.title')}</h1>
      </div>

      <div className="flex flex-1 items-center justify-center px-4">
        <p className="text-sm text-ink-tertiary">{t('mapPage.comingSoon')}</p>
      </div>

      <BottomNav />
    </main>
  )
}
