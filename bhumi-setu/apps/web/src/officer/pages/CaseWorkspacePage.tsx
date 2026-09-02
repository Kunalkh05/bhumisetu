import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { request } from '../../api/client';

type RiskState =
  | { kind: 'scored'; band: string; probability: number; factors: readonly RiskFactor[] }
  | { kind: 'not_scored'; reason: string }
  | { kind: 'scored_unmonitored'; band: string; probability: number; generated_at: string };

interface RiskFactor {
  readonly label: string;
  readonly direction: 'increases' | 'decreases';
  readonly magnitude: number;
}

interface CaseWorkspace {
  readonly id: number;
  readonly case_reference: string;
  readonly project: { readonly id: number; readonly name: string };
  readonly stage_key: string;
  readonly stage_deadline: string | null;
  readonly stage_entered_on: string;
  readonly remaining_days: number | null;
  readonly parcels: readonly ParcelSummary[];
  readonly ownership_records: readonly OwnershipSummary[];
  readonly notices: readonly NoticeSummary[];
  readonly objections: readonly ObjectionSummary[];
  readonly awards: readonly AwardSummary[];
  readonly validation_issues: readonly ValidationIssueSummary[];
  readonly documents: readonly DocumentSummary[];
  readonly timeline: readonly TimelineEvent[];
  readonly risk: RiskState;
  readonly internal_notes?: readonly string[];
  readonly entity_version: number;
}

interface ParcelSummary {
  readonly id: number;
  readonly survey_number: string;
  readonly village: string;
  readonly extent: string;
  readonly extent_unit: string;
}

interface OwnershipSummary {
  readonly id: number;
  readonly parcel_id: number;
  readonly owner_name?: string;
  readonly interest_type: string;
  readonly share: string;
  readonly valid_from: string;
}

interface NoticeSummary {
  readonly id: number;
  readonly notice_type: string;
  readonly issue_date: string;
  readonly response_deadline: string;
  readonly breach_state: string;
}

interface ObjectionSummary {
  readonly id: number;
  readonly received_on: string;
  readonly disposal_state: string;
  readonly disposal_date: string | null;
}

interface AwardSummary {
  readonly id: number;
  readonly ownership_record_id: number;
  readonly total_amount: string;
  readonly disbursement_state: string;
}

interface ValidationIssueSummary {
  readonly id: number;
  readonly rule_id: string;
  readonly severity: string;
  readonly resolution_state: string;
}

interface DocumentSummary {
  readonly id: number;
  readonly document_type: string;
  readonly original_filename: string;
  readonly processing_state: string;
}

interface TimelineEvent {
  readonly id: number;
  readonly event_type: string;
  readonly occurrence_time: string;
}

function useCaseWorkspace(caseId: string | undefined) {
  return useQuery({
    queryKey: ['case-workspace', caseId],
    enabled: Boolean(caseId),
    queryFn: () => request<CaseWorkspace>(`/cases/${caseId}/workspace`),
  });
}

export function CaseWorkspacePage() {
  const { caseId } = useParams();
  const { data, isLoading, error } = useCaseWorkspace(caseId);
  const deadline = useMemo(() => deadlineText(data), [data]);

  if (!caseId) {
    return <StatusMessage title="Case not selected" detail="The route did not include a case id." />;
  }

  if (isLoading) {
    return <StatusMessage title="Loading case" detail="Fetching current case workspace." />;
  }

  if (error || !data) {
    return <StatusMessage title="Case unavailable" detail="The workspace could not be loaded." />;
  }

  return (
    <section aria-labelledby="case-title" className="space-y-6">
      <header className="flex flex-col gap-3 border-b border-surface-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-ink-muted">Case reference</p>
          <h1 id="case-title" className="text-2xl font-semibold text-ink">
            {data.case_reference}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">{data.project.name}</p>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm lg:text-right">
          <dt className="text-ink-subtle">Stage</dt>
          <dd className="font-medium text-ink">{data.stage_key}</dd>
          <dt className="text-ink-subtle">Deadline</dt>
          <dd className="font-medium text-ink">{deadline}</dd>
        </dl>
      </header>

      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <div className="space-y-4">
          <Section title="Parcels" empty={data.parcels.length === 0 ? 'No parcels linked.' : null}>
            <Rows
              rows={data.parcels}
              columns={['Survey', 'Village', 'Extent']}
              render={(parcel) => [
                parcel.survey_number,
                parcel.village,
                `${parcel.extent} ${parcel.extent_unit}`,
              ]}
            />
          </Section>

          <Section
            title="Current Ownership"
            empty={data.ownership_records.length === 0 ? 'No current ownership records.' : null}
          >
            <Rows
              rows={data.ownership_records}
              columns={['Owner', 'Interest', 'Share', 'From']}
              render={(record) => [
                record.owner_name ?? 'Redacted',
                record.interest_type,
                record.share,
                record.valid_from,
              ]}
            />
          </Section>

          <Section title="Notices" empty={data.notices.length === 0 ? 'No notices issued.' : null}>
            <Rows
              rows={data.notices}
              columns={['Type', 'Issued', 'Response Deadline', 'State']}
              render={(notice) => [
                notice.notice_type,
                notice.issue_date,
                notice.response_deadline,
                notice.breach_state,
              ]}
            />
          </Section>

          <Section
            title="Objections"
            empty={data.objections.length === 0 ? 'No objections recorded.' : null}
          >
            <Rows
              rows={data.objections}
              columns={['Received', 'State', 'Disposed']}
              render={(objection) => [
                objection.received_on,
                objection.disposal_state,
                objection.disposal_date ?? 'Open',
              ]}
            />
          </Section>
        </div>

        <aside className="space-y-4">
          <RiskPanel risk={data.risk} />

          <Section title="Awards" empty={data.awards.length === 0 ? 'No awards recorded.' : null}>
            <Rows
              rows={data.awards}
              columns={['Owner Record', 'Amount', 'State']}
              render={(award) => [
                String(award.ownership_record_id),
                award.total_amount,
                award.disbursement_state,
              ]}
            />
          </Section>

          <Section
            title="Validation Issues"
            empty={data.validation_issues.length === 0 ? 'No open validation issues.' : null}
          >
            <Rows
              rows={data.validation_issues}
              columns={['Rule', 'Severity', 'State']}
              render={(issue) => [issue.rule_id, issue.severity, issue.resolution_state]}
            />
          </Section>

          <Section title="Documents" empty={data.documents.length === 0 ? 'No documents uploaded.' : null}>
            <Rows
              rows={data.documents}
              columns={['Type', 'File', 'State']}
              render={(document) => [
                document.document_type,
                document.original_filename,
                document.processing_state,
              ]}
            />
          </Section>

          {data.internal_notes ? (
            <Section
              title="Internal Notes"
              empty={data.internal_notes.length === 0 ? 'No internal notes.' : null}
            >
              <ul className="space-y-2 text-sm text-ink-muted">
                {data.internal_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </Section>
          ) : null}
        </aside>
      </div>

      <Section title="Timeline" empty={data.timeline.length === 0 ? 'No events recorded.' : null}>
        <ol className="divide-y divide-surface-border">
          {data.timeline.map((event) => (
            <li key={event.id} className="flex items-center justify-between py-2 text-sm">
              <span className="font-medium text-ink">{event.event_type}</span>
              <time className="text-ink-muted" dateTime={event.occurrence_time}>
                {event.occurrence_time}
              </time>
            </li>
          ))}
        </ol>
      </Section>
    </section>
  );
}

function deadlineText(data: CaseWorkspace | undefined): string {
  if (!data?.stage_deadline) {
    return 'Not set';
  }
  if (data.remaining_days === null) {
    return data.stage_deadline;
  }
  return `${data.stage_deadline} (${data.remaining_days} days)`;
}

function StatusMessage({ title, detail }: { readonly title: string; readonly detail: string }) {
  return (
    <section aria-labelledby="status-title">
      <h1 id="status-title" className="text-xl font-semibold text-ink">
        {title}
      </h1>
      <p className="mt-2 text-sm text-ink-muted">{detail}</p>
    </section>
  );
}

function Section({
  title,
  empty,
  children,
}: {
  readonly title: string;
  readonly empty: string | null;
  readonly children: React.ReactNode;
}) {
  const headingId = `section-${title.toLowerCase().replaceAll(' ', '-')}`;
  return (
    <section className="rounded border border-surface-border bg-surface p-4" aria-labelledby={headingId}>
      <h2 id={headingId} className="text-sm font-semibold uppercase text-ink-subtle">
        {title}
      </h2>
      <div className="mt-3">{empty ? <p className="text-sm text-ink-muted">{empty}</p> : children}</div>
    </section>
  );
}

function Rows<T>({
  rows,
  columns,
  render,
}: {
  readonly rows: readonly T[];
  readonly columns: readonly string[];
  readonly render: (row: T) => readonly string[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-full text-left text-sm">
        <thead>
          <tr className="border-b border-surface-border text-xs uppercase text-ink-subtle">
            {columns.map((column) => (
              <th key={column} scope="col" className="py-2 pr-3 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="border-b border-surface-border last:border-0">
              {render(row).map((value, columnIndex) => (
                <td key={`${rowIndex}-${columnIndex}`} className="break-words py-2 pr-3 text-ink">
                  {value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RiskPanel({ risk }: { readonly risk: RiskState }) {
  if (risk.kind === 'not_scored') {
    return (
      <Section title="Risk" empty={null}>
        <p className="text-sm font-medium text-risk-unscored">Not scored</p>
        <p className="mt-1 text-sm text-ink-muted">{risk.reason}</p>
      </Section>
    );
  }

  if (risk.kind === 'scored_unmonitored') {
    return (
      <Section title="Risk" empty={null}>
        <p className="text-sm font-medium text-severity-major">
          {risk.band} - {(risk.probability * 100).toFixed(1)}%
        </p>
        <p className="mt-1 text-sm text-ink-muted">Monitoring unavailable since {risk.generated_at}</p>
      </Section>
    );
  }

  return (
    <Section title="Risk" empty={null}>
      <p className="text-sm font-medium text-ink">
        {risk.band} - {(risk.probability * 100).toFixed(1)}%
      </p>
      <ul className="mt-2 space-y-1 text-sm text-ink-muted">
        {risk.factors.map((factor) => (
          <li key={factor.label}>
            {factor.label}: {factor.direction} by {factor.magnitude}
          </li>
        ))}
      </ul>
    </Section>
  );
}
