import { X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

type LocationPermissionModalProps = {
  onAllow: () => void
  onDeny: () => void
}

// 위치 권한을 브라우저에 물어보기 전에 뜨는 설명 모달 (Figma node-id 102:702).
// "허용"을 눌러야 그때 useGeolocation이 실제 브라우저 네이티브 권한 팝업을 띄운다.
// "위치기반 서비스 이용약관 보기"는 실제 약관 페이지(/terms/location)로 이동하는 링크다
// (2026-09-13 — 처음엔 Figma 목업에 이동 경로가 없어 텍스트로만 뒀는데, 약관 페이지가
// 생긴 뒤 실제 링크로 바꿨다). 로그인 여부와 상관없이 볼 수 있어야 해서 이 라우트는
// `RequireAuth` 밖에 있다(App.tsx 참고).
export function LocationPermissionModal({ onAllow, onDeny }: LocationPermissionModalProps) {
  const { t } = useTranslation()

  return (
    <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
      <button type="button" aria-label="닫기" className="absolute inset-0 bg-black/40" onClick={onDeny} />
      <div className="absolute inset-0 flex items-center justify-center px-6" onClick={onDeny}>
        <div
          className="relative w-full rounded-3xl bg-white px-5 pb-6 pt-6 text-center"
          onClick={(event) => event.stopPropagation()}
        >
          <button type="button" onClick={onDeny} aria-label="닫기" className="absolute right-5 top-5">
            <X size={24} className="text-ink" />
          </button>

          <p className="font-brand text-2xl font-bold text-primary">여운</p>

          <div className="mt-4 rounded-2xl bg-[#fff5f0] p-4 text-left">
            <p className="text-base font-bold text-ink">{t('locationConsent.title')}</p>
            <p className="mt-2 whitespace-pre-line text-xs leading-relaxed text-[#9c8a80]">
              {t('locationConsent.body')}
            </p>
            <Link to="/terms/location" className="mt-5 block text-center text-xs font-medium text-primary">
              {t('locationConsent.terms')} →
            </Link>
          </div>

          <div className="mt-5 flex gap-3">
            <button
              type="button"
              onClick={onDeny}
              className="flex-1 rounded-full border border-primary py-3 text-sm font-medium text-primary"
            >
              {t('locationConsent.deny')}
            </button>
            <button
              type="button"
              onClick={onAllow}
              className="flex-1 rounded-full bg-primary py-3 text-sm font-medium text-white"
            >
              {t('locationConsent.allow')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
