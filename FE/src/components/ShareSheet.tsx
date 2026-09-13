import { Link2 } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import kakaoIcon from '../assets/icons/kakao.svg'
import lineIcon from '../assets/icons/line.svg'
import whatsappIcon from '../assets/icons/whatsapp.svg'
import xIcon from '../assets/icons/x.svg'
import { copyShareLink, shareToKakao, shareToLine, shareToWhatsApp, shareToX } from '../lib/share'
import { BottomSheet } from './BottomSheet'

type ShareSheetProps = {
  url: string
  title: string
  description?: string
  imageUrl: string
  // 카카오톡 카드 버튼 문구. 명소는 "촬영지 보러가기", 코스는 "나만의 코스 보러가기"처럼
  // 공유 대상에 맞게 각 페이지에서 넘긴다. 안 넘기면 shareToKakao의 기본값("자세히 보기")을 쓴다.
  kakaoButtonLabel?: string
  onClose: () => void
}

// 명소·작품·코스 상세 화면 공유하기. 인스타그램·위챗은 외부 웹사이트가 쓸 수 있는 공식 공유
// 방법이 없어서(각각 네이티브 앱 전용 딥링크, 자체 앱 내장 브라우저 전용) 뺐다(2026-09-13 확인).
// 별도 취소 버튼은 없다 — BottomSheet 배경(딤)을 탭하면 닫힌다(2026-09-13 사용자 디자인).
export function ShareSheet({ url, title, description, imageUrl, kakaoButtonLabel, onClose }: ShareSheetProps) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  function handleKakao() {
    shareToKakao({ url, title, description, imageUrl, buttonLabel: kakaoButtonLabel }).catch(() => {})
    onClose()
  }

  function handleX() {
    shareToX({ url, title, description })
    onClose()
  }

  function handleLine() {
    shareToLine({ url })
    onClose()
  }

  function handleWhatsApp() {
    shareToWhatsApp({ url, title, description })
    onClose()
  }

  function handleCopy() {
    copyShareLink(url)
      .then(() => {
        setCopied(true)
        setTimeout(onClose, 1000)
      })
      .catch(() => {})
  }

  return (
    <BottomSheet onClose={onClose}>
      <div className="px-5 pb-4 pt-3">
        <p className="text-lg font-bold text-ink">{t('share.title')}</p>
        <p className="mt-1 text-sm text-ink-tertiary">{t('share.subtitle')}</p>
      </div>

      <div className="border-t border-divider" />

      <div className="flex flex-col">
        <button type="button" onClick={handleCopy} className="flex w-full items-center gap-5 px-5 py-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-ink-tertiary/20">
            <Link2 size={18} className="text-ink-secondary" />
          </span>
          <span className="text-[15px] font-medium text-ink">{copied ? t('share.copied') : t('share.copyLink')}</span>
        </button>
        <button type="button" onClick={handleKakao} className="flex w-full items-center gap-5 px-5 py-3">
          <img src={kakaoIcon} alt="" className="h-10 w-10 shrink-0 rounded-xl" />
          <span className="text-[15px] font-medium text-ink">{t('share.kakao')}</span>
        </button>
        <button type="button" onClick={handleX} className="flex w-full items-center gap-5 px-5 py-3">
          <img src={xIcon} alt="" className="h-10 w-10 shrink-0 rounded-xl" />
          <span className="text-[15px] font-medium text-ink">{t('share.x')}</span>
        </button>
        <button type="button" onClick={handleLine} className="flex w-full items-center gap-5 px-5 py-3">
          <img src={lineIcon} alt="" className="h-10 w-10 shrink-0 rounded-xl" />
          <span className="text-[15px] font-medium text-ink">{t('share.line')}</span>
        </button>
        <button type="button" onClick={handleWhatsApp} className="flex w-full items-center gap-5 px-5 py-3">
          <img src={whatsappIcon} alt="" className="h-10 w-10 shrink-0 rounded-xl" />
          <span className="text-[15px] font-medium text-ink">{t('share.whatsapp')}</span>
        </button>
      </div>
    </BottomSheet>
  )
}
