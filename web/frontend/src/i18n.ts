import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import en from './locales/en'
import zh from './locales/zh'

const resources = {
  en: { translation: en },
  zh: { translation: zh },
}

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    supportedLngs: ['en', 'zh'],
    nonExplicitSupportedLngs: true,
    load: 'languageOnly',
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
    detection: { order: ['querystring', 'localStorage', 'navigator'], caches: ['localStorage'] },
  })

export default i18n
