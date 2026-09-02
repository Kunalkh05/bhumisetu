import { useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { request } from '../../api/client';
import { useVersionedMutation, type Versioned } from '../../api/hooks/useVersionedMutation';
import { ConflictDialog } from '../conflicts/ConflictDialog';
import { useConflictDialog } from '../conflicts/useConflictDialog';
import { DocumentViewer, type ExtractedFieldBox } from '../documents/DocumentViewer';

interface DocumentViewerPayload {
  readonly id: number;
  readonly content_type: string;
  readonly grant_url: string;
  readonly fields: readonly ExtractedFieldBox[];
}

interface FieldReviewBody {
  readonly action: 'confirm' | 'correct';
  readonly corrected_value?: string;
}

function fieldEntity(field: ExtractedFieldBox): Versioned {
  return { id: String(field.id), entity_version: field.entity_version };
}

export function DocumentViewerPage() {
  const { documentId } = useParams();
  const [pageNumber, setPageNumber] = useState(1);
  const [pageCount, setPageCount] = useState(1);
  const [zoom, setZoom] = useState(1.25);
  const [selectedFieldId, setSelectedFieldId] = useState<number | null>(null);
  const [corrections, setCorrections] = useState<Record<number, string>>({});

  const query = useQuery({
    queryKey: ['document-viewer', documentId],
    enabled: Boolean(documentId),
    queryFn: () => request<DocumentViewerPayload>(`/documents/${documentId}/viewer`),
  });
  const mutation = useVersionedMutation<ExtractedFieldBox, FieldReviewBody>({
    path: (entity) => `/fields/${entity.id}`,
    invalidates: [['document-viewer', documentId]],
  });
  const conflict = useConflictDialog<FieldReviewBody>(mutation.mutate);

  const fieldsOnPage = useMemo(
    () => query.data?.fields.filter((field) => field.page_number === pageNumber) ?? [],
    [pageNumber, query.data],
  );

  if (!documentId) {
    return <StatusMessage title="Document not selected" />;
  }
  if (query.isLoading) {
    return <StatusMessage title="Loading document" />;
  }
  if (query.error || !query.data) {
    return <StatusMessage title="Document unavailable" />;
  }

  return (
    <section aria-labelledby="document-title" className="space-y-4">
      <header className="flex flex-col gap-3 border-b border-surface-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-ink-muted">Document</p>
          <h1 id="document-title" className="text-2xl font-semibold text-ink">
            {query.data.id}
          </h1>
          <p className="mt-1 text-sm text-ink-muted">{query.data.content_type}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setPageNumber((value) => Math.max(1, value - 1))}
            className="rounded border border-surface-border px-3 py-2 text-sm"
          >
            Previous
          </button>
          <span className="text-sm text-ink-muted">
            Page {pageNumber} of {pageCount}
          </span>
          <button
            type="button"
            onClick={() => setPageNumber((value) => Math.min(pageCount, value + 1))}
            className="rounded border border-surface-border px-3 py-2 text-sm"
          >
            Next
          </button>
          <input
            aria-label="Zoom"
            type="range"
            min="0.75"
            max="2"
            step="0.25"
            value={zoom}
            onChange={(event) => setZoom(Number(event.target.value))}
          />
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <DocumentViewer
          url={query.data.grant_url}
          contentType={query.data.content_type}
          fields={query.data.fields}
          selectedFieldId={selectedFieldId}
          zoom={zoom}
          pageNumber={pageNumber}
          onPageChange={setPageNumber}
          onPageCount={setPageCount}
        />

        <aside className="space-y-3">
          {fieldsOnPage.length === 0 ? (
            <p className="rounded border border-surface-border bg-surface p-4 text-sm text-ink-muted">
              No extracted fields on this page.
            </p>
          ) : (
            fieldsOnPage.map((field) => (
              <section
                key={field.id}
                className="rounded border border-surface-border bg-surface p-4"
                onFocus={() => setSelectedFieldId(field.id)}
                onMouseEnter={() => setSelectedFieldId(field.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-mono text-sm text-ink">{field.field_name}</h2>
                    <p className="mt-1 text-sm text-ink-muted">{field.review_state}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      mutation.mutate(
                        { entity: fieldEntity(field), body: { action: 'confirm' } },
                        { onError: (error) => conflict.onConflict(error as never, { body: { action: 'confirm' } }) },
                      )
                    }
                    className="rounded bg-severity-advisory px-3 py-2 text-sm font-medium text-ink-inverse"
                  >
                    Confirm
                  </button>
                </div>
                <label className="mt-3 block text-sm text-ink-muted">
                  Corrected value
                  <input
                    className="mt-1 w-full rounded border border-surface-border px-3 py-2 text-ink"
                    value={corrections[field.id] ?? field.extracted_value ?? ''}
                    onChange={(event) =>
                      setCorrections((values) => ({ ...values, [field.id]: event.target.value }))
                    }
                  />
                </label>
                <button
                  type="button"
                  onClick={() => {
                    const body: FieldReviewBody = {
                      action: 'correct',
                      corrected_value: corrections[field.id] ?? field.extracted_value ?? '',
                    };
                    mutation.mutate(
                      { entity: fieldEntity(field), body },
                      { onError: (error) => conflict.onConflict(error as never, { body }) },
                    );
                  }}
                  className="mt-3 rounded border border-surface-border px-3 py-2 text-sm text-ink"
                >
                  Save Correction
                </button>
              </section>
            ))
          )}
        </aside>
      </div>

      <ConflictDialog
        conflict={conflict.conflict}
        onClose={conflict.close}
        onResubmit={conflict.resubmitWithCurrentVersion}
      />
    </section>
  );
}

function StatusMessage({ title }: { readonly title: string }) {
  return (
    <section aria-labelledby="document-status">
      <h1 id="document-status" className="text-xl font-semibold text-ink">
        {title}
      </h1>
    </section>
  );
}
