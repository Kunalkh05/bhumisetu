import { PagePlaceholder } from './PagePlaceholder';

export function InterventionQueuePage() {
  return (
    <PagePlaceholder
      title="Intervention queue"
      task="24.2"
      requirements="21.7, 21.8"
      note="Ordered by Priority_Score; reports the oldest computation time on the page so a stale ranking is visible."
    />
  );
}
