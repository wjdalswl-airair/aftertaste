import i18next from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import ko from './locales/ko.json'

// 국적을 고르지 않으면 한국어가 기본값이다 (DETAIL_SPEC 4장, 7장).
i18next.use(initReactI18next).init({
  resources: {
    ko: { translation: ko },
    en: { translation: en },
  },
  lng: 'ko',
  fallbackLng: 'ko',
  interpolation: { escapeValue: false },
})

export default i18next
