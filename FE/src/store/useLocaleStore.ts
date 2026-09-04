import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// 국적이 아니라 언어를 직접 고르는 방식으로 바뀌었다 (2026-09-04, 언어 5개로 늘어나며 국적↔언어
// 1:1 매핑이 더 이상 안 맞아서). PRD/DETAIL_SPEC 갱신 완료.
export type Language = 'ko' | 'en' | 'ja' | 'zh-CN' | 'zh-TW'

type LocaleState = {
  language: Language
  setLocale: (language: Language) => void
}

// 비로그인 사용자의 선택은 기기(localStorage)에만 저장한다 (DETAIL_SPEC 4장).
export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      language: 'ko',
      setLocale: (language) => set({ language }),
    }),
    { name: 'locale-storage' },
  ),
)
