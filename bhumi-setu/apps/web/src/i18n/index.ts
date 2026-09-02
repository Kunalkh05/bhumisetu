import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

export const supportedLanguages = ['en', 'hi', 'mr'] as const;
export type SupportedLanguage = (typeof supportedLanguages)[number];

const namespace = 'translation';
const storedLanguageKey = 'bhumisetu.officer.language';
const loadedLanguages = new Set<SupportedLanguage>();

const localeLoaders: Record<SupportedLanguage, () => Promise<{ default: Record<string, string> }>> = {
  en: () => import('./locales/en.json'),
  hi: () => import('./locales/hi.json'),
  mr: () => import('./locales/mr.json'),
};

function isSupportedLanguage(value: string): value is SupportedLanguage {
  return supportedLanguages.includes(value as SupportedLanguage);
}

function preferredLanguage(): SupportedLanguage {
  const stored = window.localStorage.getItem(storedLanguageKey);
  if (stored && isSupportedLanguage(stored)) {
    return stored;
  }
  const browserLanguage = window.navigator.language.split('-')[0] ?? 'en';
  return isSupportedLanguage(browserLanguage) ? browserLanguage : 'en';
}

async function loadLocale(language: SupportedLanguage): Promise<void> {
  if (loadedLanguages.has(language)) {
    return;
  }
  const bundle = await localeLoaders[language]();
  i18n.addResourceBundle(language, namespace, bundle.default, true, true);
  loadedLanguages.add(language);
}

export async function changeOfficerLanguage(language: SupportedLanguage): Promise<void> {
  await loadLocale(language);
  window.localStorage.setItem(storedLanguageKey, language);
  await i18n.changeLanguage(language);
}

function reportMissingKey(language: string, key: string, fallbackValue: string | undefined): void {
  void fetch('/internal/i18n/missing', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      language,
      namespace,
      key,
      fallback_value: fallbackValue ?? null,
      expected_version: 1,
    }),
  }).catch(() => undefined);
}

export const i18nReady = (async () => {
  const initialLanguage = preferredLanguage();
  const initialBundle = await localeLoaders[initialLanguage]();
  loadedLanguages.add(initialLanguage);

  await i18n.use(initReactI18next).init({
    lng: initialLanguage,
    fallbackLng: 'en',
    defaultNS: namespace,
    ns: [namespace],
    resources: {
      [initialLanguage]: {
        [namespace]: initialBundle.default,
      },
    },
    interpolation: {
      escapeValue: false,
    },
    saveMissing: true,
    missingKeyHandler: (languages, _namespace, key, fallbackValue) => {
      const language = Array.isArray(languages) ? languages[0] : languages;
      reportMissingKey(language ?? initialLanguage, key, fallbackValue);
    },
    react: {
      useSuspense: false,
    },
  });
})();

export { i18n };
