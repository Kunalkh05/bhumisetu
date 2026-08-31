import { paths } from '../routes/paths';

export interface NavItem {
  readonly label: string;
  readonly to: string;
  /** Requirement this destination exists to satisfy, for traceability. */
  readonly requirement: string;
}

export const navItems: readonly NavItem[] = [
  { label: 'Dashboard', to: paths.dashboard, requirement: 'R22' },
  { label: 'Cases', to: paths.cases, requirement: 'R5, R23' },
  { label: 'Map', to: paths.map, requirement: 'R16' },
  { label: 'Intervention queue', to: paths.queue, requirement: 'R21' },
  { label: 'Validation issues', to: paths.issues, requirement: 'R14' },
  { label: 'Import batches', to: paths.imports, requirement: 'R30' },
];
