import i18next from 'i18next'
import { Globe } from 'lucide-react'
import { useState } from 'react'
import { updateLocale } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'
import { useLocaleStore, type Language } from '../store/useLocaleStore'

// 국적이 아니라 언어를 직접 고른다 (2026-09-04). nationality는 더 이상 UI에서 안 받는다 —
// BE Member.nationality는 선택 필드라 안 보내도 문제없다 (BE DETAIL_SPEC 6-1 #10).
const OPTIONS: { language: Language; label: string }[] = [
  { language: 'ko', label: '한국어' },
  { language: 'en', label: 'English' },
  { language: 'ja', label: '日本語' },
  { language: 'zh-CN', label: '简体中文' },
  { language: 'zh-TW', label: '繁體中文' },
]

export function LanguageSheet() {
  const [open, setOpen] = useState(false)
  const language = useLocaleStore((state) => state.language)
  const setLocale = useLocaleStore((state) => state.setLocale)
  const member = useAuthStore((state) => state.member)

  function handleSelect(option: (typeof OPTIONS)[number]) {
    setLocale(option.language)
    i18next.changeLanguage(option.language)

    if (member) {
      updateLocale({ language: option.language }).catch(() => {
        // 저장 실패해도 화면 언어 전환 자체는 그대로 유지한다.
      })
    }
    setOpen(false)
  }

  return (
    <>
      <button type="button" onClick={() => setOpen(true)} aria-label="언어 선택">
        <Globe size={22} className="text-ink" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 mx-auto w-full max-w-[480px]">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute inset-x-0 bottom-0 flex flex-col">
            <div className="w-full animate-[sheet-up_0.2s_ease-out] rounded-t-2xl bg-white p-4 pb-8">
              {OPTIONS.map((option) => (
                <button
                  key={option.language}
                  type="button"
                  onClick={() => handleSelect(option)}
                  className={`block w-full rounded-lg px-4 py-3 text-center ${
                    option.language === language ? 'font-bold text-primary' : 'text-ink'
                  }`}
                >
                  {option.label}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="mt-2 block w-full py-3 text-center text-ink-tertiary"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
