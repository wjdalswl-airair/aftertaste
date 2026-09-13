import { ArrowLeft } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import { BottomNav } from '../components/BottomNav'
import { LocationTermsContent } from '../components/LocationTermsContent'
import { PrivacyPolicyContent } from '../components/PrivacyPolicyContent'
import { TermsOfServiceContent } from '../components/TermsOfServiceContent'

type TermSlug = 'service' | 'privacy' | 'location'

const TERM_TITLE_KEYS: Record<TermSlug, string> = {
  service: 'myPage.termsMenuTerms',
  privacy: 'myPage.termsMenuPrivacy',
  location: 'myPage.termsMenuLocation',
}

const TERM_CONTENT: Record<TermSlug, () => React.JSX.Element> = {
  service: TermsOfServiceContent,
  privacy: PrivacyPolicyContent,
  location: LocationTermsContent,
}

function isTermSlug(value: string | undefined): value is TermSlug {
  return value === 'service' || value === 'privacy' || value === 'location'
}

// 약관 목록(TermsListPage)에서 항목 하나를 눌렀을 때 들어오는 상세 화면.
// 세 화면(이용약관/개인정보처리방침/위치기반 서비스 이용약관) 모두 실제 문구가 확정돼
// 각각의 Content 컴포넌트로 보여준다.
export function TermsDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { slug } = useParams<{ slug: string }>()

  if (!isTermSlug(slug)) {
    return <Navigate to="/terms" replace />
  }

  const titleKey = TERM_TITLE_KEYS[slug]
  const Content = TERM_CONTENT[slug]

  return (
    <main className="flex min-h-dvh flex-col gap-6 pb-24">
      <header className="grid min-h-16 grid-cols-[24px_1fr_24px] items-center px-4 pt-2">
        <button type="button" onClick={() => navigate(-1)} aria-label="뒤로가기">
          <ArrowLeft size={24} className="text-ink" />
        </button>
        <h1 className="text-center text-lg font-bold text-ink">{t(titleKey)}</h1>
      </header>

      <Content />

      <BottomNav />
    </main>
  )
}
