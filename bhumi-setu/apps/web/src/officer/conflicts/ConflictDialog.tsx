import type { EntityVersionConflictDetail } from '../../api/errors';

interface ConflictDialogProps {
  readonly conflict: EntityVersionConflictDetail | null;
  readonly onClose: () => void;
  readonly onResubmit: (currentVersion: number) => void;
}

function displayValue(value: unknown): string {
  if (value === null) {
    return 'null';
  }
  if (value === undefined) {
    return 'not submitted';
  }
  if (typeof value === 'string') {
    return value || 'empty string';
  }
  return JSON.stringify(value);
}

export function ConflictDialog({ conflict, onClose, onResubmit }: ConflictDialogProps) {
  if (!conflict) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="conflict-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/35 p-4"
    >
      <section className="max-h-[90vh] w-full max-w-3xl overflow-auto rounded bg-surface shadow-xl">
        <header className="border-b border-surface-border px-5 py-4">
          <h2 id="conflict-title" className="text-base font-semibold text-ink">
            Version conflict
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Current version {conflict.current_version} was changed by{' '}
            <span className="font-mono">{conflict.competing_actor_id}</span> at{' '}
            <time dateTime={conflict.competing_occurrence_time}>
              {conflict.competing_occurrence_time}
            </time>
            .
          </p>
        </header>

        <div className="px-5 py-4">
          <table className="w-full table-fixed border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-surface-border text-xs uppercase text-ink-subtle">
                <th scope="col" className="w-1/4 py-2 pr-3 font-medium">
                  Attribute
                </th>
                <th scope="col" className="w-3/8 px-3 py-2 font-medium">
                  Submitted
                </th>
                <th scope="col" className="w-3/8 py-2 pl-3 font-medium">
                  Current
                </th>
              </tr>
            </thead>
            <tbody>
              {conflict.conflicting_attributes.map((item) => (
                <tr key={item.attribute} className="border-b border-surface-border last:border-0">
                  <th scope="row" className="break-words py-3 pr-3 align-top font-mono text-xs text-ink">
                    {item.attribute}
                  </th>
                  <td className="break-words px-3 py-3 align-top text-ink-muted">
                    {displayValue(item.submitted)}
                  </td>
                  <td className="break-words py-3 pl-3 align-top text-ink">
                    {displayValue(item.current)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <footer className="flex justify-end gap-3 border-t border-surface-border px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-surface-border px-3 py-2 text-sm text-ink hover:bg-surface-sunken"
          >
            Close
          </button>
          <button
            type="button"
            onClick={() => onResubmit(conflict.current_version)}
            className="rounded bg-severity-advisory px-3 py-2 text-sm font-medium text-ink-inverse hover:opacity-95"
          >
            Resubmit with current version
          </button>
        </footer>
      </section>
    </div>
  );
}
