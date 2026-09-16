import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { BottomNav } from '../components/BottomNav'

// 하단 탭 "코스" 자리 표시 화면 (2026-09-16). MapPage가 처음에 그랬듯, 실제 코스 둘러보기
// 화면은 이후 Phase에서 별도로 구현한다.
export function CoursePage() {
  const { t } = useTranslation()

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid grid-cols-[1fr_auto_1fr] items-center px-4 pt-4">
        <Link to="/" className="font-brand text-2xl font-bold text-primary">여운</Link>
        <h1 className="text-lg font-bold text-ink">{t('coursePage.title')}</h1>
        <div />
      </header>

      <div className="flex flex-1 items-center justify-center px-4">
        <p className="text-sm text-ink-tertiary">{t('coursePage.empty')}</p>
      </div>

      <BottomNav />
    </main>
  )
}
