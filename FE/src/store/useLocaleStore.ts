import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// 국적이 아니라 언어를 직접 고르는 방식으로 바뀌었다 (2026-09-04, 언어 5개로 늘어나며 국적↔언어
// 1:1 매핑이 더 이상 안 맞아서). PRD/DETAIL_SPEC 갱신 완료.
export type Language = 'ko' | 'en' | 'ja' | 'zh-CN' | 'zh-TW'

// 처음 방문한 사용자는 기기 언어로 추측해서 시작한다 (2026-09-06) — 외국인이 1차 타겟인데
// 계속 한국어로 시작하면, 로그인 전엔 메인 화면 헤더의 언어 버튼을 직접 눌러야만 바뀌어서
// 그 버튼을 못 찾으면 계속 한국어로 남는 문제가 있었다. 지원 안 하는 언어권은 한국어보다
// 영어가 더 통할 확률이 높아 영어로 폴백한다.
export function detectInitialLanguage(): Language {
  const browserLang = navigator.language?.toLowerCase() ?? ''

  if (browserLang.startsWith('ko')) return 'ko'
  if (browserLang.startsWith('ja')) return 'ja'
  if (browserLang.startsWith('zh')) {
    return browserLang.includes('tw') || browserLang.includes('hk') || browserLang.includes('mo') ? 'zh-TW' : 'zh-CN'
  }
  return 'en'
}

type LocaleState = {
  language: Language
  setLocale: (language: Language) => void
}

// 비로그인 사용자의 선택은 기기(localStorage)에만 저장한다 (DETAIL_SPEC 4장).
// 이미 저장된 값이 있으면 persist가 그 값을 우선 쓰고, 최초 방문일 때만 detectInitialLanguage가 쓰인다.
export const useLocaleStore = create<LocaleState>()(
  persist(
    (set) => ({
      language: detectInitialLanguage(),
      setLocale: (language) => set({ language }),
    }),
    { name: 'locale-storage' },
  ),
)
