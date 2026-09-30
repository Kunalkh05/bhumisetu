import React, { useState } from 'react';
import { LineChart as LineChartIcon, Table as TableIcon, Info, HelpCircle } from 'lucide-react';
import { OfficerSurvivalRisk } from '../../../types/survival';

interface SurvivalCurveChartProps {
  riskData: OfficerSurvivalRisk;
  language?: 'en' | 'hi';
}

export const SurvivalCurveChart: React.FC<SurvivalCurveChartProps> = ({ riskData, language = 'en' }) => {
  const [viewMode, setViewMode] = useState<'SURVIVAL' | 'EVENT'>('SURVIVAL');
  const [showTable, setShowTable] = useState(false);
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Discrete coordinate points from API
  const points = [
    { t: 0, s: 1.0, e: 0.0, label: '0d', isExtrapolated: false },
    { t: 30, s: riskData.survival_probability_30d, e: riskData.event_probability_30d, label: '30d', isExtrapolated: false },
    { t: 90, s: riskData.survival_probability_90d, e: riskData.event_probability_90d, label: '90d', isExtrapolated: false },
    { t: 180, s: riskData.survival_probability_180d, e: riskData.event_probability_180d, label: '180d', isExtrapolated: true },
    { t: 365, s: riskData.survival_probability_365d, e: riskData.event_probability_365d, label: '365d', isExtrapolated: true },
    { t: 730, s: riskData.survival_probability_730d, e: riskData.event_probability_730d, label: '730d', isExtrapolated: true },
  ];

  // SVG dimensions & padding
  const width = 680;
  const height = 260;
  const padding = { top: 25, right: 30, bottom: 40, left: 55 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  // Scale functions
  const maxT = 730;
  const scaleX = (t: number) => padding.left + (t / maxT) * chartW;
  const scaleY = (val: number) => padding.top + (1 - Math.max(0, Math.min(1, val))) * chartH;

  const empiricalCutoffT = 148;
  const cutoffX = scaleX(empiricalCutoffT);

  // Generate SVG path for empirical segment (0 to 148d approx via points 0, 30, 90)
  const valKey = viewMode === 'SURVIVAL' ? 's' : 'e';
  const empiricalPoints = points.filter((p) => p.t <= 90);
  const extrapolatedPoints = points.filter((p) => p.t >= 90);

  const makePath = (pts: typeof points) => {
    return pts
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(p.t).toFixed(1)} ${scaleY(p[valKey]).toFixed(1)}`)
      .join(' ');
  };

  const empiricalPath = makePath(empiricalPoints);
  const extrapolatedPath = makePath(extrapolatedPoints);

  const activeValLabel = viewMode === 'SURVIVAL' ? 'Survival Probability S(t)' : 'Transition Probability P(t)';

  return (
    <div className="gov-surface-card p-5 space-y-4" role="region" aria-label="Survival Curve Visualization">
      {/* Header & Controls */}
      <div className="flex items-center justify-between flex-wrap gap-3 border-b border-slate-100 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <LineChartIcon className="w-4 h-4 text-[#002642]" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {language === 'en' ? 'Estimated Survival & Transition Curve' : 'जीवित रहने एवं संक्रमण का वक्र'}
            </h4>
          </div>
          <p className="text-[11px] text-slate-500 mt-0.5">
            {language === 'en'
              ? 'Parametric Cox regression trajectory across 730 days. Solid line indicates empirical cohort; dashed indicates statistical extrapolation.'
              : '730 दिनों में कॉक्स प्रतिगमन प्रक्षेपवक्र। ठोस रेखा अनुभवजन्य समूह को दर्शाती है।'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Metric View Toggle */}
          <div className="bg-slate-100 p-0.5 rounded-lg flex items-center text-xs font-semibold">
            <button
              onClick={() => setViewMode('SURVIVAL')}
              className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                viewMode === 'SURVIVAL' ? 'bg-white text-[#002642] shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Survival S(t)
            </button>
            <button
              onClick={() => setViewMode('EVENT')}
              className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                viewMode === 'EVENT' ? 'bg-white text-[#002642] shadow-xs font-bold' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Event P(t) = 1 - S(t)
            </button>
          </div>

          {/* Table fallback toggle */}
          <button
            onClick={() => setShowTable(!showTable)}
            aria-expanded={showTable}
            aria-label="Toggle accessible tabular data"
            className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 text-xs flex items-center gap-1 cursor-pointer"
            title="Toggle Accessible Data Table"
          >
            <TableIcon className="w-3.5 h-3.5" />
            <span className="text-[11px] font-medium hidden sm:inline">Table</span>
          </button>
        </div>
      </div>

      {/* SVG Survival Curve */}
      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto max-w-full font-mono text-[10px]"
          role="img"
          aria-label={`Survival curve showing ${activeValLabel} across 730 days`}
        >
          {/* Y-axis gridlines & labels */}
          {[0.0, 0.25, 0.5, 0.75, 1.0].map((v) => {
            const y = scaleY(v);
            return (
              <g key={v}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={width - padding.right}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeDasharray="3 3"
                />
                <text x={padding.left - 8} y={y + 3} textAnchor="end" fill="#64748b" className="text-[9px]">
                  {(v * 100).toFixed(0)}%
                </text>
              </g>
            );
          })}

          {/* X-axis tick lines & labels */}
          {[0, 90, 180, 365, 730].map((t) => {
            const x = scaleX(t);
            return (
              <g key={t}>
                <line x1={x} y1={padding.top} x2={x} y2={height - padding.bottom} stroke="#f1f5f9" />
                <line x1={x} y1={height - padding.bottom} x2={x} y2={height - padding.bottom + 5} stroke="#94a3b8" />
                <text x={x} y={height - padding.bottom + 18} textAnchor="middle" fill="#64748b">
                  {t}d
                </text>
              </g>
            );
          })}

          {/* Empirical follow-up cutoff line (148 days) */}
          <line
            x1={cutoffX}
            y1={padding.top}
            x2={cutoffX}
            y2={height - padding.bottom}
            stroke="#f59e0b"
            strokeWidth="1.5"
            strokeDasharray="4 2"
          />
          <text
            x={cutoffX + 4}
            y={padding.top + 10}
            fill="#b45309"
            className="text-[9px] font-sans font-bold"
          >
            Follow-Up Limit (148d)
          </text>

          {/* Extrapolated region background shading */}
          <rect
            x={cutoffX}
            y={padding.top}
            width={width - padding.right - cutoffX}
            height={chartH}
            fill="#f8fafc"
            opacity="0.8"
          />

          {/* Solid line for empirical segment */}
          <path
            d={empiricalPath}
            fill="none"
            stroke="#002642"
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Dashed line for extrapolated segment */}
          <path
            d={extrapolatedPath}
            fill="none"
            stroke="#0284c7"
            strokeWidth="2.5"
            strokeDasharray="5 3"
            strokeLinecap="round"
          />

          {/* Data Points */}
          {points.map((p, idx) => {
            const cx = scaleX(p.t);
            const cy = scaleY(p[valKey]);
            const isHovered = hoveredIndex === idx;

            return (
              <g key={p.t} onMouseEnter={() => setHoveredIndex(idx)} onMouseLeave={() => setHoveredIndex(null)}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHovered ? 6 : 4}
                  fill={p.isExtrapolated ? '#0284c7' : '#002642'}
                  stroke="#ffffff"
                  strokeWidth="2"
                  className="transition-all cursor-pointer"
                />
                {isHovered && (
                  <g>
                    <rect
                      x={cx - 45}
                      y={cy - 30}
                      width="90"
                      height="22"
                      rx="4"
                      fill="#0f172a"
                      className="drop-shadow-md"
                    />
                    <text x={cx} y={cy - 16} fill="#ffffff" textAnchor="middle" className="text-[10px] font-mono">
                      {p.label}: {(p[valKey] * 100).toFixed(1)}%
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Axis Titles */}
          <text
            x={width / 2}
            y={height - 5}
            textAnchor="middle"
            fill="#475569"
            className="text-[10px] font-sans font-medium"
          >
            Elapsed Time in Current Transition (Days)
          </text>
          <text
            transform={`rotate(-90) translate(-${height / 2}, 15)`}
            textAnchor="middle"
            fill="#475569"
            className="text-[10px] font-sans font-medium"
          >
            {activeValLabel}
          </text>
        </svg>
      </div>

      {/* Legend & Notation */}
      <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1 flex-wrap gap-2">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 bg-[#002642] inline-block" />
            <span>Empirical Follow-Up (&le; 148d)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 border-t border-dashed border-[#0284c7] inline-block" />
            <span>Extrapolated Horizon (&gt; 148d)</span>
          </div>
        </div>

        <span className="text-[10px] text-slate-400">
          Source: Fitted Cox Proportional Hazards Model ($S_0(t)^{'{'} \exp(\eta) {'}'}$)
        </span>
      </div>

      {/* Accessible Table Fallback */}
      {showTable && (
        <div className="mt-3 overflow-x-auto border border-slate-200 rounded-lg">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
              <tr>
                <th className="p-2">Horizon</th>
                <th className="p-2">Days</th>
                <th className="p-2">Survival S(t)</th>
                <th className="p-2">Event P(t)</th>
                <th className="p-2">Evidence Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {points.map((p) => (
                <tr key={p.t} className={p.isExtrapolated ? 'bg-slate-50/50' : 'bg-white'}>
                  <td className="p-2 font-bold">{p.label}</td>
                  <td className="p-2">{p.t}</td>
                  <td className="p-2">{(p.s * 100).toFixed(2)}%</td>
                  <td className="p-2">{(p.e * 100).toFixed(2)}%</td>
                  <td className="p-2 font-sans text-[11px]">
                    {p.isExtrapolated ? (
                      <span className="text-amber-700 font-medium">Extrapolated (&gt; 148d)</span>
                    ) : (
                      <span className="text-emerald-700 font-medium">Empirical Cohort</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
