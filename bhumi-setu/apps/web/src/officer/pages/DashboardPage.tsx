import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { request } from '../../api/client';

interface DashboardMetric {
  readonly value?: unknown;
  readonly computed_at?: string | null;
  readonly unavailable_at?: string | null;
  readonly reason?: string | null;
}

interface BandHistoryPoint {
  readonly month: string;
  readonly band: string;
  readonly case_count: number;
}

interface DashboardPayload {
  readonly metrics: Record<string, DashboardMetric>;
  readonly stage_keys: readonly string[];
  readonly band_history: readonly BandHistoryPoint[];
}

const bandOrder = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'NOT_SCORED'] as const;
const bandClasses: Record<string, string> = {
  LOW: 'bg-risk-low',
  MEDIUM: 'bg-risk-medium',
  HIGH: 'bg-risk-high',
  CRITICAL: 'bg-risk-critical',
  NOT_SCORED: 'bg-risk-unscored',
};

export function DashboardPage() {
  const dashboardQuery = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => request<DashboardPayload>('/dashboard'),
  });
  const data = dashboardQuery.data;
  const stageCounts = objectMetric(data, 'cases_by_stage');
  const stageKeys = data?.stage_keys.length ? data.stage_keys : Object.keys(stageCounts);
  const stageTotal = sumValues(stageCounts);
  const bandCounts = objectMetric(data, 'cases_by_band');
  const history = useMemo(() => monthRows(data?.band_history ?? []), [data?.band_history]);

  return (
    <section aria-labelledby="dashboard-title" className="space-y-6">
      <header className="flex flex-col gap-3 border-b border-surface-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-ink-muted">Officer operations</p>
          <h1 id="dashboard-title" className="text-2xl font-semibold text-ink">
            Dashboard
          </h1>
        </div>
        <p className="text-sm text-ink-muted">
          {data ? `Oldest metric ${oldestMetricTime(data.metrics)}` : 'Loading.'}
        </p>
      </header>

      {dashboardQuery.error ? (
        <p className="rounded border border-severity-blocking bg-white p-3 text-sm text-severity-blocking">
          {errorText(dashboardQuery.error)}
        </p>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-4">
        <MetricTile title="Open cases" metric={metric(data, 'cases_by_stage')} value={stageTotal} />
        <MetricTile title="Breached deadlines" metric={metric(data, 'breached_deadline_count')} />
        <MetricTile title="Undisposed objections" metric={metric(data, 'undisposed_objection_count')} />
        <MetricTile title="Awarded amount" metric={metric(data, 'aggregate_awarded')} currency />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <Panel title="Stage Distribution" loading={dashboardQuery.isLoading} empty={stageKeys.length === 0}>
          <div className="space-y-3">
            {stageKeys.map((stage) => {
              const count = stageCounts[stage] ?? 0;
              const width = stageTotal > 0 ? `${Math.max(4, (count / stageTotal) * 100)}%` : '0%';
              return (
                <div key={stage} className="grid gap-2 sm:grid-cols-[11rem_1fr_4rem] sm:items-center">
                  <div className="min-w-0 text-sm font-medium text-ink">{stage}</div>
                  <div className="h-3 overflow-hidden rounded-sm bg-surface-sunken">
                    <div className="h-full rounded-sm bg-severity-advisory" style={{ width }} />
                  </div>
                  <div className="text-right text-sm tabular-nums text-ink-muted">{count}</div>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel title="Risk Bands" loading={dashboardQuery.isLoading} empty={Object.keys(bandCounts).length === 0}>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
            {bandOrder.map((band) => (
              <div key={band} className="border-b border-surface-border pb-3 last:border-b-0">
                <dt className="flex items-center gap-2 text-xs font-medium uppercase text-ink-subtle">
                  <span className={`h-2.5 w-2.5 rounded-sm ${bandClasses[band]}`} />
                  {bandLabel(band)}
                </dt>
                <dd className="mt-2 text-2xl font-semibold tabular-nums text-ink">{bandCounts[band] ?? 0}</dd>
              </div>
            ))}
          </dl>
        </Panel>
      </div>

      <Panel title="12 Month Band Trend" loading={dashboardQuery.isLoading} empty={history.length === 0}>
        <div className="overflow-x-auto">
          <div className="grid min-w-[720px] grid-cols-12 gap-3">
            {history.map((month) => (
              <div key={month.month} className="flex min-h-40 flex-col justify-end gap-1">
                <div className="flex h-32 flex-col justify-end overflow-hidden rounded-sm bg-surface-sunken">
                  {bandOrder.map((band) => {
                    const count = month.bands[band] ?? 0;
                    if (count === 0) {
                      return null;
                    }
                    return (
                      <div
                        key={band}
                        className={bandClasses[band]}
                        title={`${bandLabel(band)}: ${count}`}
                        style={{ height: `${Math.max(6, (count / month.total) * 128)}px` }}
                      />
                    );
                  })}
                </div>
                <span className="truncate text-center text-xs text-ink-muted">{formatMonth(month.month)}</span>
              </div>
            ))}
          </div>
        </div>
      </Panel>
    </section>
  );
}

function MetricTile({
  title,
  metric,
  value,
  currency = false,
}: {
  readonly title: string;
  readonly metric: DashboardMetric | undefined;
  readonly value?: number;
  readonly currency?: boolean;
}) {
  const display = value ?? scalarValue(metric);
  return (
    <section className="rounded border border-surface-border bg-surface p-4">
      <h2 className="text-sm font-medium text-ink-subtle">{title}</h2>
      {metric?.reason ? (
        <>
          <p className="mt-3 text-lg font-semibold text-severity-blocking">Unavailable</p>
          <p className="mt-1 text-xs text-ink-muted">{metric.reason}</p>
        </>
      ) : (
        <>
          <p className="mt-3 text-3xl font-semibold tabular-nums text-ink">
            {currency ? formatCurrency(display) : formatNumber(display)}
          </p>
          <p className="mt-1 text-xs text-ink-muted">{formatDateTime(metric?.computed_at)}</p>
        </>
      )}
    </section>
  );
}

function Panel({
  title,
  loading,
  empty,
  children,
}: {
  readonly title: string;
  readonly loading: boolean;
  readonly empty: boolean;
  readonly children: React.ReactNode;
}) {
  const id = `dashboard-${title.toLowerCase().replaceAll(' ', '-')}`;
  return (
    <section className="rounded border border-surface-border bg-surface p-4" aria-labelledby={id}>
      <h2 id={id} className="text-sm font-semibold uppercase text-ink-subtle">
        {title}
      </h2>
      <div className="mt-4">
        {loading ? <p className="text-sm text-ink-muted">Loading.</p> : null}
        {!loading && empty ? <p className="text-sm text-ink-muted">No dashboard data.</p> : null}
        {!loading && !empty ? children : null}
      </div>
    </section>
  );
}

function metric(data: DashboardPayload | undefined, key: string): DashboardMetric | undefined {
  return data?.metrics[key];
}

function objectMetric(data: DashboardPayload | undefined, key: string): Record<string, number> {
  const value = metric(data, key)?.value;
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {};
  }
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([itemKey, itemValue]) => [
      itemKey,
      Number(itemValue) || 0,
    ]),
  );
}

function scalarValue(metricValue: DashboardMetric | undefined): number | string | null {
  if (metricValue?.value === undefined || metricValue.value === null) {
    return null;
  }
  if (typeof metricValue.value === 'number' || typeof metricValue.value === 'string') {
    return metricValue.value;
  }
  return null;
}

function sumValues(values: Record<string, number>): number {
  return Object.values(values).reduce((total, value) => total + value, 0);
}

function monthRows(points: readonly BandHistoryPoint[]) {
  const byMonth = new Map<string, Record<string, number>>();
  for (const point of points) {
    const bands = byMonth.get(point.month) ?? {};
    bands[point.band] = (bands[point.band] ?? 0) + point.case_count;
    byMonth.set(point.month, bands);
  }
  return [...byMonth.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .slice(-12)
    .map(([month, bands]) => ({ month, bands, total: Math.max(1, sumValues(bands)) }));
}

function oldestMetricTime(metrics: Record<string, DashboardMetric>): string {
  const times = Object.values(metrics)
    .map((entry) => entry.computed_at ?? entry.unavailable_at)
    .filter((entry): entry is string => Boolean(entry))
    .sort();
  return formatDateTime(times[0]);
}

function formatNumber(value: number | string | null): string {
  if (value === null) {
    return '-';
  }
  return new Intl.NumberFormat('en-IN').format(Number(value));
}

function formatCurrency(value: number | string | null): string {
  if (value === null) {
    return '-';
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(Number(value));
}

function formatMonth(value: string): string {
  return new Intl.DateTimeFormat('en-IN', { month: 'short', year: '2-digit' }).format(new Date(value));
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

function bandLabel(band: string): string {
  return band === 'NOT_SCORED' ? 'Not scored' : band;
}

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : 'Dashboard could not be loaded.';
}
