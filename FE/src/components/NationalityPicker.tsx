import i18next from 'i18next'
import { updateLocale } from '../api/auth'
import { useAuthStore } from '../store/useAuthStore'
import { useLocaleStore, type Nationality } from '../store/useLocaleStore'

const OPTIONS: { nationality: Nationality; language: 'ko' | 'en'; label: string }[] = [
  { nationality: 'KR', language: 'ko', label: '한국어' },
  { nationality: 'OTHER', language: 'en', label: 'English' },
]

export function NationalityPicker() {
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
  }

  return (
    <div className="flex gap-2 px-4">
      {OPTIONS.map((option) => (
        <button
          key={option.nationality}
          type="button"
          onClick={() => handleSelect(option)}
          className={
            option.nationality === nationality
              ? 'rounded-full bg-primary px-4 py-2 text-sm text-white'
              : 'rounded-full border border-divider px-4 py-2 text-sm text-ink'
          }
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
