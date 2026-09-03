import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { request } from '../../api/client';
import { paths } from '../routes/paths';

interface RecommendedAction {
  readonly action_id: string;
  readonly label_key: string;
  readonly reason_key: string;
  readonly severity: string;
}

interface QueueItem {
  readonly case_id: number;
  readonly case_reference: string;
  readonly stage_key: string;
  readonly risk_band: string | null;
  readonly remaining_days: number | null;
  readonly priority_score: string | number | null;
  readonly priority_computed_at: string | null;
  readonly recommended_actions: readonly RecommendedAction[];
}

interface QueuePayload {
  readonly items: readonly QueueItem[];
  readonly oldest_priority_computed_at: string | null;
  readonly limit: number;
  readonly offset: number;
}

export function InterventionQueuePage() {
  const queueQuery = useQuery({
    queryKey: ['intervention-queue'],
    queryFn: () => request<QueuePayload>('/queue?limit=50&offset=0'),
  });
  const items = queueQuery.data?.items ?? [];

  return (
    <section aria-labelledby="queue-title" className="space-y-6">
      <header className="flex flex-col gap-3 border-b border-surface-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-ink-muted">Officer operations</p>
          <h1 id="queue-title" className="text-2xl font-semibold text-ink">
            Intervention queue
          </h1>
        </div>
        <p className="text-sm text-ink-muted">
          Oldest score {formatDateTime(queueQuery.data?.oldest_priority_computed_at)}
        </p>
      </header>

      {queueQuery.error ? (
        <p className="rounded border border-severity-blocking bg-white p-3 text-sm text-severity-blocking">
          {errorText(queueQuery.error)}
        </p>
      ) : null}

      <section className="rounded border border-surface-border bg-surface p-4" aria-labelledby="queue-table-title">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <h2 id="queue-table-title" className="text-sm font-semibold uppercase text-ink-subtle">
            Ranked Cases
          </h2>
          <span className="text-sm tabular-nums text-ink-muted">
            {queueQuery.isLoading ? 'Loading.' : `${items.length} shown`}
          </span>
        </div>

        {!queueQuery.isLoading && items.length === 0 && !queueQuery.error ? (
          <p className="mt-4 text-sm text-ink-muted">No open cases in the queue.</p>
        ) : null}

        {items.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs uppercase text-ink-subtle">
                  <th className="py-2 pr-3 font-medium">Case</th>
                  <th className="py-2 pr-3 font-medium">Stage</th>
                  <th className="py-2 pr-3 font-medium">Risk</th>
                  <th className="py-2 pr-3 text-right font-medium">Remaining</th>
                  <th className="py-2 pr-3 text-right font-medium">Priority</th>
                  <th className="py-2 pr-3 font-medium">Actions</th>
                  <th className="py-2 pr-0 font-medium">Computed</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.case_id} className="border-b border-surface-border last:border-0 hover:bg-surface-sunken">
                    <td className="py-3 pr-3">
                      <Link
                        className="font-medium text-severity-advisory hover:underline"
                        to={paths.case(String(item.case_id))}
                      >
                        {item.case_reference}
                      </Link>
                    </td>
                    <td className="py-3 pr-3 font-medium text-ink">{item.stage_key}</td>
                    <td className="py-3 pr-3">
                      <RiskPill band={item.risk_band} />
                    </td>
                    <td className={`py-3 pr-3 text-right tabular-nums ${remainingClass(item.remaining_days)}`}>
                      {formatRemaining(item.remaining_days)}
                    </td>
                    <td className="py-3 pr-3 text-right text-lg font-semibold tabular-nums text-ink">
                      {formatPriority(item.priority_score)}
                    </td>
                    <td className="py-3 pr-3">
                      <div className="flex max-w-md flex-wrap gap-1.5">
                        {item.recommended_actions.length === 0 ? (
                          <span className="text-sm text-ink-muted">None</span>
                        ) : (
                          item.recommended_actions.map((action) => (
                            <span
                              key={action.action_id}
                              className="rounded border border-surface-border bg-white px-2 py-1 text-xs font-medium text-ink"
                              title={action.reason_key}
                            >
                              {action.label_key}
                            </span>
                          ))
                        )}
                      </div>
                    </td>
                    <td className="py-3 pr-0 text-ink-muted">{formatDateTime(item.priority_computed_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </section>
  );
}

function RiskPill({ band }: { readonly band: string | null }) {
  const label = band ?? 'Not scored';
  const className =
    band === 'LOW'
      ? 'bg-risk-low/10 text-risk-low'
      : band === 'MEDIUM'
        ? 'bg-risk-medium/10 text-risk-medium'
        : band === 'HIGH'
          ? 'bg-risk-high/10 text-risk-high'
          : band === 'CRITICAL'
            ? 'bg-risk-critical/10 text-risk-critical'
            : 'bg-risk-unscored/10 text-risk-unscored';
  return <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ${className}`}>{label}</span>;
}

function remainingClass(value: number | null): string {
  if (value === null) {
    return 'text-ink-muted';
  }
  if (value < 0) {
    return 'text-deadline-breached';
  }
  if (value <= 7) {
    return 'text-deadline-near';
  }
  return 'text-deadline-ok';
}

function formatRemaining(value: number | null): string {
  if (value === null) {
    return '-';
  }
  if (value < 0) {
    return `${Math.abs(value)}d late`;
  }
  return `${value}d`;
}

function formatPriority(value: string | number | null): string {
  if (value === null) {
    return '-';
  }
  return Number(value).toFixed(1);
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return '-';
  }
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Queue could not be loaded.';
}
