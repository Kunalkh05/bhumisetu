import { NavLink, Outlet } from 'react-router-dom';
import { navItems } from './navItems';

/**
 * Officer portal chrome: skip link, sidebar, and the routed outlet.
 *
 * Deliberately holds no data fetching. Whether the portal talks to live
 * endpoints or a mock fetcher is a decision at the query-client seam, not here,
 * so the shell is unaffected by it.
 */
export function AppShell() {
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
          <span className="text-sm font-semibold tracking-wide text-ink">BHUMISETU</span>
          <span className="mt-0.5 block text-xs text-ink-subtle">Officer portal</span>
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
                {item.label}
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
