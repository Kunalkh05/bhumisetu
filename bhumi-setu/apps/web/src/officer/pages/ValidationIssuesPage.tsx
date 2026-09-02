import { useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { request } from '../../api/client';
import { ApiError, EntityVersionConflictError } from '../../api/errors';

interface ValidationIssue {
  readonly id: number;
  readonly case_id: number;
  readonly rule_id: string;
  readonly fingerprint: string;
  readonly severity: 'BLOCKING' | 'MAJOR' | 'MINOR' | 'ADVISORY' | string;
  readonly offending_entities: Record<string, unknown>;
  readonly observed_values: Record<string, unknown>;
  readonly detected_at: string;
  readonly resolution_state: string;
  readonly resolved_at: string | null;
  readonly entity_version: number;
}

interface ValidationHistory {
  readonly id: number;
  readonly issue_id: number;
  readonly prior_state: string | null;
  readonly new_state: string;
  readonly actor_id: string;
  readonly reason: string | null;
  readonly occurrence_time: string;
}

interface TimelineEvent {
  readonly id: number;
  readonly event_type: string;
  readonly entity_type: string;
  readonly entity_id: number;
  readonly occurrence_time: string;
  readonly recording_time: string;
  readonly payload: Record<string, unknown>;
}

interface ProcessingDocument {
  readonly id: number;
  readonly case_id: number | null;
  readonly parcel_id: number | null;
  readonly document_type: string;
  readonly original_filename: string;
  readonly byte_size: number;
  readonly content_type: string;
  readonly uploaded_at: string;
  readonly processing_state: 'QUEUED' | 'PROCESSING' | string;
  readonly failure_reason: string | null;
  readonly detected_script: string | null;
  readonly entity_version: number;
}

const severityRank: Record<string, number> = {
  BLOCKING: 3,
  MAJOR: 2,
  MINOR: 1,
  ADVISORY: 0,
};

export function ValidationIssuesPage() {
  const [selectedIssueId, setSelectedIssueId] = useState<number | null>(null);
  const [waiverReason, setWaiverReason] = useState('');
  const [mutationMessage, setMutationMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const issuesQuery = useQuery({
    queryKey: ['validation-issues'],
    queryFn: () => request<readonly ValidationIssue[]>('/issues'),
  });
  const processingQuery = useQuery({
    queryKey: ['processing-documents'],
    queryFn: () => request<readonly ProcessingDocument[]>('/documents/processing'),
  });

  const orderedIssues = useMemo(
    () =>
      [...(issuesQuery.data ?? [])].sort((left, right) => {
        const severity = (severityRank[right.severity] ?? -1) - (severityRank[left.severity] ?? -1);
        if (severity !== 0) {
          return severity;
        }
        return Date.parse(left.detected_at) - Date.parse(right.detected_at);
      }),
    [issuesQuery.data],
  );
  const selectedIssue =
    orderedIssues.find((issue) => issue.id === selectedIssueId) ?? orderedIssues[0] ?? null;

  const historyQuery = useQuery({
    queryKey: ['validation-issue-history', selectedIssue?.id],
    enabled: Boolean(selectedIssue),
    queryFn: () => request<readonly ValidationHistory[]>(`/issues/${selectedIssue?.id}/history`),
  });
  const timelineQuery = useQuery({
    queryKey: ['case-timeline', selectedIssue?.case_id],
    enabled: Boolean(selectedIssue?.case_id),
    queryFn: () => request<readonly TimelineEvent[]>(`/cases/${selectedIssue?.case_id}/timeline`),
  });

  const waiverMutation = useMutation({
    mutationFn: (issue: ValidationIssue) =>
      request<ValidationIssue>(`/issues/${issue.id}/waive`, {
        method: 'POST',
        body: {
          reason: waiverReason.trim(),
          expected_version: issue.entity_version,
        },
      }),
    onSuccess: async () => {
      setWaiverReason('');
      setMutationMessage('Waiver recorded.');
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['validation-issues'] }),
        queryClient.invalidateQueries({ queryKey: ['validation-issue-history'] }),
      ]);
    },
    onError: (error) => {
      if (error instanceof EntityVersionConflictError) {
        setMutationMessage('Issue changed while the waiver was open. Review the refreshed issue before retrying.');
        void queryClient.invalidateQueries({ queryKey: ['validation-issues'] });
        return;
      }
      if (error instanceof ApiError) {
        setMutationMessage(error.message);
        return;
      }
      setMutationMessage('Waiver could not be recorded.');
    },
  });

  function submitWaiver(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedIssue || waiverReason.trim().length === 0) {
      return;
    }
    setMutationMessage(null);
    waiverMutation.mutate(selectedIssue);
  }

  return (
    <section aria-labelledby="validation-title" className="space-y-6">
      <header className="flex flex-col gap-3 border-b border-surface-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-ink-muted">Officer operations</p>
          <h1 id="validation-title" className="text-2xl font-semibold text-ink">
            Validation issues
          </h1>
        </div>
        <IssueTotals issues={orderedIssues} />
      </header>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.4fr)_minmax(360px,0.8fr)]">
        <Panel
          title="Issue Queue"
          loading={issuesQuery.isLoading}
          error={issuesQuery.error}
          empty={orderedIssues.length === 0 ? 'No open validation issues.' : null}
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr className="border-b border-surface-border text-xs uppercase text-ink-subtle">
                  <th className="py-2 pr-3 font-medium">Severity</th>
                  <th className="py-2 pr-3 font-medium">Rule</th>
                  <th className="py-2 pr-3 font-medium">Case</th>
                  <th className="py-2 pr-3 font-medium">Detected</th>
                  <th className="py-2 pr-3 font-medium">State</th>
                </tr>
              </thead>
              <tbody>
                {orderedIssues.map((issue) => (
                  <tr
                    key={issue.id}
                    className={`cursor-pointer border-b border-surface-border last:border-0 ${
                      selectedIssue?.id === issue.id ? 'bg-accent/10' : 'hover:bg-surface-muted'
                    }`}
                    onClick={() => {
                      setSelectedIssueId(issue.id);
                      setMutationMessage(null);
                    }}
                  >
                    <td className="py-2 pr-3">
                      <SeverityPill severity={issue.severity} />
                    </td>
                    <td className="break-words py-2 pr-3 font-medium text-ink">{issue.rule_id}</td>
                    <td className="py-2 pr-3 text-ink-muted">#{issue.case_id}</td>
                    <td className="py-2 pr-3 text-ink-muted">{formatDateTime(issue.detected_at)}</td>
                    <td className="py-2 pr-3 text-ink">{issue.resolution_state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>

        <Panel
          title="Waiver Flow"
          loading={issuesQuery.isLoading}
          error={issuesQuery.error}
          empty={!selectedIssue ? 'Select an issue to review waiver options.' : null}
        >
          {selectedIssue ? (
            <div className="space-y-4">
              <dl className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-2 text-sm">
                <dt className="text-ink-subtle">Issue</dt>
                <dd className="font-medium text-ink">#{selectedIssue.id}</dd>
                <dt className="text-ink-subtle">Fingerprint</dt>
                <dd className="break-all text-ink">{selectedIssue.fingerprint}</dd>
                <dt className="text-ink-subtle">Entities</dt>
                <dd className="text-ink">{compactJson(selectedIssue.offending_entities)}</dd>
                <dt className="text-ink-subtle">Observed</dt>
                <dd className="text-ink">{compactJson(selectedIssue.observed_values)}</dd>
              </dl>

              <form className="space-y-3" onSubmit={submitWaiver}>
                <label className="block text-sm font-medium text-ink" htmlFor="waiver-reason">
                  Waiver reason
                </label>
                <textarea
                  id="waiver-reason"
                  className="min-h-28 w-full rounded border border-surface-border bg-white px-3 py-2 text-sm text-ink outline-none focus:border-accent"
                  value={waiverReason}
                  onChange={(event) => setWaiverReason(event.target.value)}
                />
                <button
                  type="submit"
                  className="rounded bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={waiverReason.trim().length === 0 || waiverMutation.isPending}
                >
                  {waiverMutation.isPending ? 'Recording' : 'Record waiver'}
                </button>
                {mutationMessage ? <p className="text-sm text-ink-muted">{mutationMessage}</p> : null}
              </form>
            </div>
          ) : null}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel
          title="Resolution History"
          loading={historyQuery.isLoading}
          error={historyQuery.error}
          empty={(historyQuery.data?.length ?? 0) === 0 ? 'No resolution history for the selected issue.' : null}
        >
          <ol className="divide-y divide-surface-border">
            {(historyQuery.data ?? []).map((entry) => (
              <li key={entry.id} className="py-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-ink">
                    {entry.prior_state ?? 'New'} to {entry.new_state}
                  </span>
                  <time className="text-ink-muted" dateTime={entry.occurrence_time}>
                    {formatDateTime(entry.occurrence_time)}
                  </time>
                </div>
                <p className="mt-1 text-ink-muted">{entry.reason ?? 'No reason recorded.'}</p>
              </li>
            ))}
          </ol>
        </Panel>

        <Panel
          title="Case Timeline"
          loading={timelineQuery.isLoading}
          error={timelineQuery.error}
          empty={(timelineQuery.data?.length ?? 0) === 0 ? 'No case events recorded.' : null}
        >
          <ol className="divide-y divide-surface-border">
            {[...(timelineQuery.data ?? [])]
              .sort((left, right) => Date.parse(left.occurrence_time) - Date.parse(right.occurrence_time))
              .map((event) => (
                <li key={event.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                  <span className="font-medium text-ink">{event.event_type}</span>
                  <time className="text-ink-muted" dateTime={event.occurrence_time}>
                    {formatDateTime(event.occurrence_time)}
                  </time>
                </li>
              ))}
          </ol>
        </Panel>
      </div>

      <Panel
        title="Document Processing"
        loading={processingQuery.isLoading}
        error={processingQuery.error}
        empty={(processingQuery.data?.length ?? 0) === 0 ? 'No documents are queued or processing.' : null}
      >
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(processingQuery.data ?? []).map((document) => (
            <article key={document.id} className="rounded border border-surface-border bg-white p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-ink">{document.original_filename}</p>
                  <p className="mt-1 text-xs text-ink-muted">
                    {document.document_type} - {formatBytes(document.byte_size)}
                  </p>
                </div>
                <StatePill state={document.processing_state} />
              </div>
              <dl className="mt-3 grid grid-cols-[80px_1fr] gap-x-3 gap-y-1 text-xs">
                <dt className="text-ink-subtle">Case</dt>
                <dd className="text-ink">{document.case_id ? `#${document.case_id}` : 'Parcel only'}</dd>
                <dt className="text-ink-subtle">Uploaded</dt>
                <dd className="text-ink">{formatDateTime(document.uploaded_at)}</dd>
              </dl>
            </article>
          ))}
        </div>
      </Panel>
    </section>
  );
}

function IssueTotals({ issues }: { readonly issues: readonly ValidationIssue[] }) {
  const counts = issues.reduce<Record<string, number>>((accumulator, issue) => {
    accumulator[issue.severity] = (accumulator[issue.severity] ?? 0) + 1;
    return accumulator;
  }, {});

  return (
    <dl className="flex flex-wrap gap-3 text-sm">
      {['BLOCKING', 'MAJOR', 'MINOR', 'ADVISORY'].map((severity) => (
        <div key={severity} className="min-w-24 rounded border border-surface-border bg-surface px-3 py-2">
          <dt className="text-xs uppercase text-ink-subtle">{severity}</dt>
          <dd className="text-lg font-semibold text-ink">{counts[severity] ?? 0}</dd>
        </div>
      ))}
    </dl>
  );
}

function Panel({
  title,
  loading,
  error,
  empty,
  children,
}: {
  readonly title: string;
  readonly loading: boolean;
  readonly error: unknown;
  readonly empty: string | null;
  readonly children: ReactNode;
}) {
  const headingId = `panel-${title.toLowerCase().replaceAll(' ', '-')}`;
  return (
    <section className="rounded border border-surface-border bg-surface p-4" aria-labelledby={headingId}>
      <h2 id={headingId} className="text-sm font-semibold uppercase text-ink-subtle">
        {title}
      </h2>
      <div className="mt-3">
        {loading ? <p className="text-sm text-ink-muted">Loading.</p> : null}
        {!loading && error ? <p className="text-sm text-severity-blocking">{errorText(error)}</p> : null}
        {!loading && !error && empty ? <p className="text-sm text-ink-muted">{empty}</p> : null}
        {!loading && !error && !empty ? children : null}
      </div>
    </section>
  );
}

function SeverityPill({ severity }: { readonly severity: string }) {
  const className =
    severity === 'BLOCKING'
      ? 'bg-severity-blocking/10 text-severity-blocking'
      : severity === 'MAJOR'
        ? 'bg-severity-major/10 text-severity-major'
        : 'bg-surface-muted text-ink';

  return <span className={`inline-flex rounded px-2 py-1 text-xs font-medium ${className}`}>{severity}</span>;
}

function StatePill({ state }: { readonly state: string }) {
  const className =
    state === 'PROCESSING' ? 'bg-accent/10 text-accent' : 'bg-risk-unscored/10 text-risk-unscored';
  return <span className={`shrink-0 rounded px-2 py-1 text-xs font-medium ${className}`}>{state}</span>;
}

function compactJson(value: Record<string, unknown>): string {
  const text = JSON.stringify(value);
  if (text.length <= 120) {
    return text;
  }
  return `${text.slice(0, 117)}...`;
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'Request failed.';
}
