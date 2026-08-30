import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Nationality = 'KR' | 'OTHER'
export type Language = 'ko' | 'en'

type LocaleState = {
  // 아직 고르지 않았으면 null. 이때 language는 기본값인 'ko'.
  nationality: Nationality | null
  language: Language
  setLocale: (nationality: Nationality, language: Language) => void
}

// 비로그인 사용자의 선택은 기기(localStorage)에만 저장한다 (DETAIL_SPEC 4장).
export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      nationality: null,
      language: 'ko',
      setLocale: (nationality, language) => set({ nationality, language }),
    }),
    { name: 'locale-storage' },
  ),
)
