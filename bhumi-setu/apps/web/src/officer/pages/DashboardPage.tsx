import { PagePlaceholder } from './PagePlaceholder';

export function DashboardPage() {
  return (
    <PagePlaceholder
      title="Dashboard"
      task="24.4"
      requirements="22.1, 22.2, 22.3, 22.4"
      note="Metrics carry their own computation time per R22.4, and a metric that fails to compute is labelled unavailable rather than voiding its neighbours (R22.6)."
    />
  );
}
