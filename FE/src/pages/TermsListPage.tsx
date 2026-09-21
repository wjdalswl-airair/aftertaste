import { ArrowLeft, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { BottomNav } from '../components/BottomNav'

const TERMS: { slug: string; labelKey: string }[] = [
  { slug: 'service', labelKey: 'myPage.termsMenuTerms' },
  { slug: 'privacy', labelKey: 'myPage.termsMenuPrivacy' },
  { slug: 'location', labelKey: 'myPage.termsMenuLocation' },
]

// 마이페이지 "약관 모아보기"에서 들어오는 화면. 뒤로가기 + 제목 헤더, 그 아래 약관 3종 목록.
// 항목을 누르면 각 약관의 상세 화면(TermsDetailPage, /terms/:slug)으로 이동한다.
export function TermsListPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <main className="flex min-h-dvh flex-col pb-24">
      <header className="-mb-6 grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-2">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <h1 className="text-center text-lg font-bold text-ink">{t('myPage.termsMenuLink')}</h1>
      </header>

      <div className="mt-4 flex flex-col">
        {TERMS.map(({ slug, labelKey }) => (
          <Link
            key={slug}
            to={`/terms/${slug}`}
            className="flex items-center justify-between border-b border-divider px-4 py-4"
          >
            <span className="text-base font-medium text-ink">{t(labelKey)}</span>
            <ChevronRight size={18} className="text-ink-tertiary" />
          </Link>
        ))}
      </div>

      <BottomNav />
    </main>
  )
}
