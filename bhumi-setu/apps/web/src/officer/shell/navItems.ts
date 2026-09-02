import { paths } from '../routes/paths';

export interface NavItem {
  readonly labelKey: string;
  readonly to: string;
  /** Requirement this destination exists to satisfy, for traceability. */
  readonly requirement: string;
}

export const navItems: readonly NavItem[] = [
  { labelKey: 'nav.dashboard', to: paths.dashboard, requirement: 'R22' },
  { labelKey: 'nav.cases', to: paths.cases, requirement: 'R5, R23' },
  { labelKey: 'nav.map', to: paths.map, requirement: 'R16' },
  { labelKey: 'nav.queue', to: paths.queue, requirement: 'R21' },
  { labelKey: 'nav.issues', to: paths.issues, requirement: 'R14' },
  { labelKey: 'nav.imports', to: paths.imports, requirement: 'R30' },
];
