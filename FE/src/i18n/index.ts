import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import { useLocaleStore } from '../store/useLocaleStore'
import en from './locales/en.json'
import ja from './locales/ja.json'
import ko from './locales/ko.json'
import zhCN from './locales/zh-CN.json'
import zhTW from './locales/zh-TW.json'

// 언어를 고르지 않으면 한국어가 기본값이다 (DETAIL_SPEC 4장, 7장).
// ja/zh-CN/zh-TW는 Claude가 en.json 기준으로 초안 번역한 것 — 사용자 검토 전이라 표현이 어색할 수 있다 (2026-09-04).
// zustand persist는 동기적으로 localStorage에서 복원되므로, 이 시점엔 이미 저장된 언어값을 읽을 수 있다.
// 이걸 안 하면 새로고침할 때마다 항상 한국어로 초기화돼서, 언어를 골랐던 사용자가 매번 다시 골라야 했다.
const initialLanguage = useLocaleStore.getState().language

i18next.use(initReactI18next).init({
  resources: {
    ko: { translation: ko },
    en: { translation: en },
    ja: { translation: ja },
    'zh-CN': { translation: zhCN },
    'zh-TW': { translation: zhTW },
  },
  lng: initialLanguage,
  fallbackLng: 'ko',
  interpolation: { escapeValue: false },
})

// <html lang>을 실제 화면 언어와 맞춰둔다. 한자는 한국어/일본어/중국어(간체·번체)가 유니코드
// 코드값을 공유해서(한자 유니코드 통합), CSS가 :lang()으로 언어별 폰트를 고르려면 이 값이
// 정확해야 한다 (index.css 참고).
document.documentElement.lang = initialLanguage
i18next.on('languageChanged', (lng) => {
  document.documentElement.lang = lng
})

export default i18next
