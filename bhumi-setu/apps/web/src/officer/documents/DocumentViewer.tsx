import { useEffect, useRef, useState } from 'react';
import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

export interface ExtractedFieldBox {
  readonly id: number;
  readonly field_name: string;
  readonly extracted_value: string | null;
  readonly review_state: string;
  readonly detected_script?: string | null;
  readonly entity_version: number;
  readonly page_number: number;
  readonly bbox_x1: number;
  readonly bbox_y1: number;
  readonly bbox_x2: number;
  readonly bbox_y2: number;
}

interface DocumentViewerProps {
  readonly url: string;
  readonly contentType: string;
  readonly fields: readonly ExtractedFieldBox[];
  readonly selectedFieldId: number | null;
  readonly zoom: number;
  readonly pageNumber: number;
  readonly onPageChange: (page: number) => void;
  readonly onPageCount: (pages: number) => void;
}

export function DocumentViewer({
  url,
  contentType,
  fields,
  selectedFieldId,
  zoom,
  pageNumber,
  onPageChange,
  onPageCount,
}: DocumentViewerProps) {
  if (contentType === 'application/pdf') {
    return (
      <PdfCanvas
        url={url}
        fields={fields}
        selectedFieldId={selectedFieldId}
        zoom={zoom}
        pageNumber={pageNumber}
        onPageChange={onPageChange}
        onPageCount={onPageCount}
      />
    );
  }

  return (
    <ImageCanvas
      url={url}
      fields={fields}
      selectedFieldId={selectedFieldId}
      pageNumber={pageNumber}
      onPageCount={onPageCount}
    />
  );
}

function PdfCanvas({
  url,
  fields,
  selectedFieldId,
  zoom,
  pageNumber,
  onPageChange,
  onPageCount,
}: Omit<DocumentViewerProps, 'contentType'>) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [renderedPage, setRenderedPage] = useState(pageNumber);

  useEffect(() => {
    let cancelled = false;
    const task = pdfjs.getDocument(url);

    async function render() {
      const document = await task.promise;
      if (cancelled) {
        return;
      }
      onPageCount(document.numPages);
      const safePage = Math.min(Math.max(pageNumber, 1), document.numPages);
      if (safePage !== pageNumber) {
        onPageChange(safePage);
        return;
      }
      const page = await document.getPage(safePage);
      const viewport = page.getViewport({ scale: zoom });
      const canvas = canvasRef.current;
      const context = canvas?.getContext('2d');
      if (!canvas || !context || cancelled) {
        return;
      }
      canvas.width = viewport.width;
      canvas.height = viewport.height;
      await page.render({ canvasContext: context, viewport }).promise;
      if (!cancelled) {
        setRenderedPage(safePage);
      }
    }

    void render();
    return () => {
      cancelled = true;
      task.destroy();
    };
  }, [onPageChange, onPageCount, pageNumber, url, zoom]);

  return (
    <DocumentSurface
      fields={fields}
      pageNumber={renderedPage}
      selectedFieldId={selectedFieldId}
    >
      <canvas ref={canvasRef} className="block max-w-full bg-surface" />
    </DocumentSurface>
  );
}

function ImageCanvas({
  url,
  fields,
  selectedFieldId,
  pageNumber,
  onPageCount,
}: Pick<DocumentViewerProps, 'url' | 'fields' | 'selectedFieldId' | 'pageNumber' | 'onPageCount'>) {
  useEffect(() => {
    onPageCount(1);
  }, [onPageCount]);

  return (
    <DocumentSurface fields={fields} pageNumber={pageNumber} selectedFieldId={selectedFieldId}>
      <img src={url} alt="" className="block max-w-full bg-surface" />
    </DocumentSurface>
  );
}

function DocumentSurface({
  children,
  fields,
  pageNumber,
  selectedFieldId,
}: {
  readonly children: React.ReactNode;
  readonly fields: readonly ExtractedFieldBox[];
  readonly pageNumber: number;
  readonly selectedFieldId: number | null;
}) {
  return (
    <div className="inline-block max-w-full overflow-auto rounded border border-surface-border bg-surface shadow-sm">
      <div className="relative inline-block">
        {children}
        {fields
          .filter((field) => field.page_number === pageNumber)
          .map((field) => (
            <span
              key={field.id}
              aria-hidden="true"
              className={[
                'absolute border-2',
                field.id === selectedFieldId
                  ? 'border-severity-blocking bg-severity-blocking/15'
                  : 'border-severity-advisory bg-severity-advisory/10',
              ].join(' ')}
              style={{
                left: `${field.bbox_x1 * 100}%`,
                top: `${field.bbox_y1 * 100}%`,
                width: `${(field.bbox_x2 - field.bbox_x1) * 100}%`,
                height: `${(field.bbox_y2 - field.bbox_y1) * 100}%`,
              }}
            />
          ))}
      </div>
    </div>
  );
}
