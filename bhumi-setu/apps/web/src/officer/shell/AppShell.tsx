import { NavLink, Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { changeOfficerLanguage, supportedLanguages, type SupportedLanguage } from '../../i18n';
import { navItems } from './navItems';

/**
 * Officer portal chrome: skip link, sidebar, and the routed outlet.
 *
 * Deliberately holds no data fetching. Whether the portal talks to live
 * endpoints or a mock fetcher is a decision at the query-client seam, not here,
 * so the shell is unaffected by it.
 */
export function AppShell() {
  const { i18n, t } = useTranslation();

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2 focus:text-sm focus:shadow"
      >
        Skip to content
      </a>

      <nav
        aria-label="Sections"
        className="border-b border-surface-border bg-surface lg:border-b-0 lg:border-r"
      >
        <div className="px-4 py-4">
          <span className="text-sm font-semibold tracking-wide text-ink">{t('app.brand')}</span>
          <span className="mt-0.5 block text-xs text-ink-subtle">{t('app.portal')}</span>
          <label className="mt-3 block text-xs font-medium text-ink-subtle" htmlFor="officer-language">
            {t('language.label')}
          </label>
          <select
            id="officer-language"
            className="mt-1 w-full rounded border border-surface-border bg-white px-2 py-1.5 text-sm text-ink"
            value={i18n.resolvedLanguage ?? i18n.language}
            onChange={(event) => void changeOfficerLanguage(event.target.value as SupportedLanguage)}
          >
            {supportedLanguages.map((language) => (
              <option key={language} value={language}>
                {t(`language.${language}`)}
              </option>
            ))}
          </select>
        </div>
        <ul className="pb-2 lg:pb-0">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  [
                    'block border-l-2 px-4 py-2 text-sm',
                    isActive
                      ? 'border-severity-advisory bg-surface-sunken font-medium text-ink'
                      : 'border-transparent text-ink-muted hover:bg-surface-sunken hover:text-ink',
                  ].join(' ')
                }
              >
                {t(item.labelKey)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <main id="main" className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
