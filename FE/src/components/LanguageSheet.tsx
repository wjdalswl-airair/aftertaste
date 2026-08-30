import i18next from 'i18next'
import { Globe } from 'lucide-react'
import { useState } from 'react'
import { updateLocale } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'
import { useLocaleStore, type Nationality } from '../store/useLocaleStore'

const OPTIONS: { nationality: Nationality; language: 'ko' | 'en'; label: string }[] = [
  { nationality: 'KR', language: 'ko', label: '한국어' },
  { nationality: 'OTHER', language: 'en', label: 'English' },
]

export function LanguageSheet() {
  const [open, setOpen] = useState(false)
  const nationality = useLocaleStore((state) => state.nationality)
  const setLocale = useLocaleStore((state) => state.setLocale)
  const member = useAuthStore((state) => state.member)

  function handleSelect(option: (typeof OPTIONS)[number]) {
    setLocale(option.nationality, option.language)
    i18next.changeLanguage(option.language)

    if (member) {
      updateLocale({ nationality: option.nationality, language: option.language }).catch(() => {
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
        <div className="fixed inset-0 z-50 flex items-end">
          <button
            type="button"
            aria-label="닫기"
            className="absolute inset-0 bg-black/40"
            onClick={() => setOpen(false)}
          />
          <div className="relative w-full animate-[sheet-up_0.2s_ease-out] rounded-t-2xl bg-white p-4 pb-8">
            {OPTIONS.map((option) => (
              <button
                key={option.nationality}
                type="button"
                onClick={() => handleSelect(option)}
                className={`block w-full rounded-lg px-4 py-3 text-center ${
                  option.nationality === nationality ? 'font-bold text-primary' : 'text-ink'
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
      )}
    </>
  )
}
