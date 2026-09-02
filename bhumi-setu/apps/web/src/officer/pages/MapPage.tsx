import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import maplibregl, { type MapLayerMouseEvent } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { paths } from '../routes/paths';

interface ParcelSelection {
  readonly parcel_id: number;
  readonly case_id: number;
  readonly survey_number: string;
  readonly extent: string;
  readonly extent_unit: string;
  readonly case_reference: string;
  readonly stage_key: string;
  readonly risk_band: string | null;
}

const riskColours = {
  LOW: '#1b6e3c',
  MEDIUM: '#8a6100',
  HIGH: '#b3480f',
  CRITICAL: '#a5122a',
  unscored: '#6b7480',
} as const;

export function MapPage() {
  const container = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const navigate = useNavigate();
  const [selection, setSelection] = useState<ParcelSelection | null>(null);

  useEffect(() => {
    if (!container.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: container.current,
      center: [73.8567, 18.5204],
      zoom: 10,
      style: {
        version: 8,
        sources: {
          parcels: {
            type: 'vector',
            tiles: ['/api/officer/gis/tiles/{z}/{x}/{y}.mvt'],
            minzoom: 0,
            maxzoom: 16,
          },
        },
        layers: [
          {
            id: 'parcel-fill',
            type: 'fill',
            source: 'parcels',
            'source-layer': 'parcels',
            paint: {
              'fill-color': [
                'match',
                ['get', 'risk_band'],
                'LOW',
                riskColours.LOW,
                'MEDIUM',
                riskColours.MEDIUM,
                'HIGH',
                riskColours.HIGH,
                'CRITICAL',
                riskColours.CRITICAL,
                riskColours.unscored,
              ],
              'fill-opacity': 0.48,
            },
          },
          {
            id: 'parcel-outline',
            type: 'line',
            source: 'parcels',
            'source-layer': 'parcels',
            paint: {
              'line-color': '#14181d',
              'line-opacity': 0.45,
              'line-width': 1,
            },
          },
        ],
      },
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
    map.on('click', 'parcel-fill', (event: MapLayerMouseEvent) => {
      const feature = event.features?.[0];
      if (!feature?.properties) {
        return;
      }
      setSelection({
        parcel_id: Number(feature.properties['id']),
        case_id: Number(feature.properties['case_id']),
        survey_number: String(feature.properties['survey_number']),
        extent: String(feature.properties['extent']),
        extent_unit: String(feature.properties['extent_unit']),
        case_reference: String(feature.properties['case_reference']),
        stage_key: String(feature.properties['stage_key']),
        risk_band: feature.properties['risk_band'] ? String(feature.properties['risk_band']) : null,
      });
    });
    map.on('mouseenter', 'parcel-fill', () => {
      map.getCanvas().style.cursor = 'pointer';
    });
    map.on('mouseleave', 'parcel-fill', () => {
      map.getCanvas().style.cursor = '';
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  return (
    <section aria-labelledby="map-title" className="space-y-4">
      <header className="flex flex-col gap-3 border-b border-surface-border pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="text-sm text-ink-muted">GIS</p>
          <h1 id="map-title" className="text-2xl font-semibold text-ink">
            Parcel Map
          </h1>
        </div>
        <RiskLegend />
      </header>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div
          ref={container}
          className="h-[min(70vh,48rem)] min-h-[30rem] rounded border border-surface-border bg-surface"
        />
        <aside className="rounded border border-surface-border bg-surface p-4">
          {selection ? (
            <div className="space-y-3">
              <div>
                <h2 className="text-sm font-semibold text-ink">{selection.case_reference}</h2>
                <p className="text-sm text-ink-muted">{selection.stage_key}</p>
              </div>
              <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
                <dt className="text-ink-subtle">Parcel</dt>
                <dd className="text-ink">{selection.survey_number}</dd>
                <dt className="text-ink-subtle">Extent</dt>
                <dd className="text-ink">
                  {selection.extent} {selection.extent_unit}
                </dd>
                <dt className="text-ink-subtle">Risk</dt>
                <dd className="text-ink">{selection.risk_band ?? 'Not scored'}</dd>
              </dl>
              <button
                type="button"
                onClick={() => navigate(paths.case(String(selection.case_id)))}
                className="w-full rounded bg-severity-advisory px-3 py-2 text-sm font-medium text-ink-inverse"
              >
                Open Case
              </button>
            </div>
          ) : (
            <p className="text-sm text-ink-muted">No parcel selected.</p>
          )}
        </aside>
      </div>
    </section>
  );
}

function RiskLegend() {
  const rows = [
    ['LOW', riskColours.LOW],
    ['MEDIUM', riskColours.MEDIUM],
    ['HIGH', riskColours.HIGH],
    ['CRITICAL', riskColours.CRITICAL],
    ['Not scored', riskColours.unscored],
  ] as const;

  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs sm:grid-cols-5">
      {rows.map(([label, colour]) => (
        <div key={label} className="flex items-center gap-2">
          <dt className="h-3 w-3 border border-surface-border" style={{ backgroundColor: colour }} />
          <dd className="text-ink-muted">{label}</dd>
        </div>
      ))}
    </dl>
  );
}
