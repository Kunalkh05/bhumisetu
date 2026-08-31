/**
 * Route paths for the officer portal.
 *
 * Declared in one place so the sidebar, breadcrumbs, and every navigate() call
 * agree. Paths are relative to the Vite base '/officer/', which the router
 * receives as its basename — the Caddyfile preserves that prefix (`handle`, not
 * `handle_path`), so the router must account for it or every link resolves one
 * level too high.
 */
export const paths = {
  dashboard: '/',
  cases: '/cases',
  case: (id = ':caseId') => `/cases/${id}`,
  map: '/map',
  queue: '/queue',
  issues: '/issues',
  imports: '/imports',
} as const;

export type RoutePath = typeof paths;
