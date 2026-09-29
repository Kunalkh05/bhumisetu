import React, { useState, useMemo } from 'react';
import { ReraZoneAggregatedStatus, ReraPerformanceStatus, ReraParcelProjectRecord } from '../../types/rera';
import { 
  BarChart3, 
  Layers, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  Building2, 
  Users, 
  ShieldAlert, 
  Info,
  Maximize2,
  Table as TableIcon,
  HelpCircle,
  MapPin,
  Sparkles,
  ChevronRight,
  Filter
} from 'lucide-react';
import { formatCurrencyINR } from '../../lib/utils';

export type ChartMetricType = 'PROJECT_COUNT' | 'LAND_AREA_HA' | 'ALLOTTEES_COUNT';
export type ChartLayoutType = 'GROUPED' | 'STACKED';

interface ReraPerformanceChartProps {
  zoneData: ReraZoneAggregatedStatus[];
  selectedZoneId?: string;
  onSelectZone?: (zoneId: string) => void;
  selectedStatus?: ReraPerformanceStatus | 'ALL';
  onSelectStatus?: (status: ReraPerformanceStatus | 'ALL') => void;
  onSelectProject?: (project: ReraParcelProjectRecord) => void;
}

export const ReraPerformanceChart: React.FC<ReraPerformanceChartProps> = ({
  zoneData,
  selectedZoneId,
  onSelectZone,
  selectedStatus = 'ALL',
  onSelectStatus,
  onSelectProject,
}) => {
  const [metric, setMetric] = useState<ChartMetricType>('PROJECT_COUNT');
  const [layout, setLayout] = useState<ChartLayoutType>('GROUPED');
  const [showTable, setShowTable] = useState<boolean>(false);
  const [hoveredBar, setHoveredBar] = useState<{
    zoneId: string;
    status: ReraPerformanceStatus;
    value: number;
    label: string;
    projects: ReraParcelProjectRecord[];
    x: number;
    y: number;
  } | null>(null);

  // Overall calculations across all zones
  const overallSummary = useMemo(() => {
    let totalProjects = 0;
    let onTrack = 0;
    let delayed = 0;
    let completed = 0;
    let lapsed = 0;
    let totalAreaHa = 0;
    let totalAllottees = 0;
    let totalSec11Breaches = 0;

    zoneData.forEach(z => {
      totalProjects += z.totalProjects;
      onTrack += z.onTrackCount;
      delayed += z.delayedCount;
      completed += z.completedCount;
      lapsed += z.lapsedCount;
      totalAreaHa += z.totalAreaOverlapHa;
      totalAllottees += z.totalAllotteesImpacted;
      totalSec11Breaches += z.sec11BreachesCount;
    });

    const delayedRate = totalProjects > 0 ? Math.round((delayed / totalProjects) * 100) : 0;
    const onTrackRate = totalProjects > 0 ? Math.round((onTrack / totalProjects) * 100) : 0;
    const completedRate = totalProjects > 0 ? Math.round((completed / totalProjects) * 100) : 0;

    return {
      totalProjects,
      onTrack,
      delayed,
      completed,
      lapsed,
      totalAreaHa: Number(totalAreaHa.toFixed(2)),
      totalAllottees,
      totalSec11Breaches,
      delayedRate,
      onTrackRate,
      completedRate,
    };
  }, [zoneData]);

  // Status configuration
  const STATUS_CONFIG: Record<ReraPerformanceStatus, {
    label: string;
    labelHi: string;
    color: string;
    hoverColor: string;
    bgBadge: string;
    textBadge: string;
    borderBadge: string;
    icon: any;
  }> = {
    ON_TRACK: {
      label: 'On-Track',
      labelHi: 'प्रगति पर / समय पर',
      color: '#138808',
      hoverColor: '#0e6706',
      bgBadge: 'bg-emerald-50',
      textBadge: 'text-emerald-800',
      borderBadge: 'border-emerald-300',
      icon: CheckCircle2,
    },
    DELAYED: {
      label: 'Delayed',
      labelHi: 'विलंबित',
      color: '#f37021',
      hoverColor: '#d95a10',
      bgBadge: 'bg-amber-50',
      textBadge: 'text-amber-800',
      borderBadge: 'border-amber-300',
      icon: Clock,
    },
    COMPLETED: {
      label: 'Completed / OC',
      labelHi: 'पूर्ण / अधिभोग प्रमाणपत्र',
      color: '#0b3866',
      hoverColor: '#082d52',
      bgBadge: 'bg-blue-50',
      textBadge: 'text-[#0b3866]',
      borderBadge: 'border-blue-300',
      icon: Building2,
    },
    LAPSED_DEFAULT: {
      label: 'Lapsed / Default',
      labelHi: 'व्यपगत / डिफ़ॉल्ट',
      color: '#dc2626',
      hoverColor: '#b91c1c',
      bgBadge: 'bg-red-50',
      textBadge: 'text-red-800',
      borderBadge: 'border-red-300',
      icon: ShieldAlert,
    },
  };

  // Extract metric value for a specific status inside a zone
  const getStatusValue = (zone: ReraZoneAggregatedStatus, status: ReraPerformanceStatus): {
    val: number;
    projects: ReraParcelProjectRecord[];
  } => {
    const projs = zone.projects.filter(p => p.performanceStatus === status);
    if (metric === 'PROJECT_COUNT') {
      return { val: projs.length, projects: projs };
    }
    if (metric === 'LAND_AREA_HA') {
      const area = projs.reduce((s, p) => s + p.overlappingAreaWithParcelHa, 0);
      return { val: Number(area.toFixed(2)), projects: projs };
    }
    if (metric === 'ALLOTTEES_COUNT') {
      const count = projs.reduce((s, p) => s + p.allottees.allotteesCount, 0);
      return { val: count, projects: projs };
    }
    return { val: projs.length, projects: projs };
  };

  // SVG Chart Dimensions & Computations
  const chartHeight = 240;
  const chartPadding = { top: 25, right: 30, bottom: 45, left: 45 };

  // Calculate maximum value for chart Y-axis scale
  const maxMetricValue = useMemo(() => {
    let max = 0;
    zoneData.forEach(z => {
      if (layout === 'GROUPED') {
        const statuses: ReraPerformanceStatus[] = ['ON_TRACK', 'DELAYED', 'COMPLETED', 'LAPSED_DEFAULT'];
        statuses.forEach(st => {
          const v = getStatusValue(z, st).val;
          if (v > max) max = v;
        });
      } else {
        // Stacked: sum of all
        const sum = (['ON_TRACK', 'DELAYED', 'COMPLETED', 'LAPSED_DEFAULT'] as ReraPerformanceStatus[])
          .reduce((s, st) => s + getStatusValue(z, st).val, 0);
        if (sum > max) max = sum;
      }
    });

    if (max === 0) return 5;
    // Round up nicely
    if (metric === 'PROJECT_COUNT') return Math.max(Math.ceil(max * 1.25), 4);
    if (metric === 'LAND_AREA_HA') return Math.max(Math.ceil(max * 1.2), 5);
    return Math.max(Math.ceil(max * 1.2), 50);
  }, [zoneData, metric, layout]);

  // Y-axis grid ticks (4 ticks)
  const yTicks = useMemo(() => {
    const ticks = [0];
    const step = maxMetricValue / 4;
    for (let i = 1; i <= 4; i++) {
      ticks.push(metric === 'PROJECT_COUNT' ? Math.round(step * i) : Number((step * i).toFixed(1)));
    }
    return ticks;
  }, [maxMetricValue, metric]);

  const getYCoordinate = (val: number) => {
    const plotHeight = chartHeight - chartPadding.top - chartPadding.bottom;
    const ratio = Math.min(val / maxMetricValue, 1);
    return chartHeight - chartPadding.bottom - ratio * plotHeight;
  };

  const metricSuffix = metric === 'LAND_AREA_HA' ? ' Ha' : metric === 'ALLOTTEES_COUNT' ? ' Units' : '';

  return (
    <div className="bg-white border border-slate-200 rounded-xs shadow-xs overflow-hidden">
      {/* Visual Header / Sub-banner */}
      <div className="p-4 sm:p-5 border-b border-slate-200 bg-[#f8fafc]">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="px-2 py-0.5 bg-[#002642] text-white font-mono text-[10px] font-bold tracking-wider uppercase rounded-xs flex items-center gap-1">
                <BarChart3 className="w-3 h-3 text-[#f37021]" />
                Corridor Performance Surveillance
              </span>
              <span className="text-[11px] font-semibold text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-xs">
                4 Active Acquisition Zones
              </span>
              <span className="text-[11px] text-amber-900 bg-amber-50 border border-amber-200 px-2 py-0.5 font-bold rounded-xs">
                {overallSummary.delayedRate}% Projects Delayed
              </span>
            </div>

            <h3 className="text-base sm:text-lg font-bold text-[#002642] flex items-center gap-2">
              <span>RERA Project Status Distributions Across Land Acquisition Zones</span>
            </h3>
            
            <p className="text-xs text-slate-600">
              Aggregated distribution of real-estate schemes (On-Track vs. Delayed vs. Completed vs. Lapsed) overlapping key infrastructure corridors.
            </p>
          </div>

          {/* Interactive Metric & Layout Switchers */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Metric Switcher */}
            <div className="flex items-center bg-slate-200/80 p-0.5 rounded-xs border border-slate-300 text-xs">
              <button
                onClick={() => setMetric('PROJECT_COUNT')}
                className={`px-2.5 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  metric === 'PROJECT_COUNT' 
                    ? 'bg-[#0b3866] text-white shadow-2xs' 
                    : 'text-slate-700 hover:text-black'
                }`}
                title="View number of registered projects in each status"
              >
                Project Count
              </button>

              <button
                onClick={() => setMetric('LAND_AREA_HA')}
                className={`px-2.5 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  metric === 'LAND_AREA_HA' 
                    ? 'bg-[#0b3866] text-white shadow-2xs' 
                    : 'text-slate-700 hover:text-black'
                }`}
                title="View total overlapping land in hectares"
              >
                Overlap Area (Ha)
              </button>

              <button
                onClick={() => setMetric('ALLOTTEES_COUNT')}
                className={`px-2.5 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  metric === 'ALLOTTEES_COUNT' 
                    ? 'bg-[#0b3866] text-white shadow-2xs' 
                    : 'text-slate-700 hover:text-black'
                }`}
                title="View total buyer allottee units affected"
              >
                Allottees Bound
              </button>
            </div>

            {/* Layout Toggle: Grouped vs Stacked */}
            <div className="flex items-center bg-slate-200/80 p-0.5 rounded-xs border border-slate-300 text-xs">
              <button
                onClick={() => setLayout('GROUPED')}
                className={`px-2 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  layout === 'GROUPED' ? 'bg-white text-[#0b3866] font-bold shadow-2xs' : 'text-slate-600'
                }`}
                title="Grouped bar view side-by-side"
              >
                Grouped
              </button>
              <button
                onClick={() => setLayout('STACKED')}
                className={`px-2 py-1 font-semibold rounded-xs transition-colors cursor-pointer ${
                  layout === 'STACKED' ? 'bg-white text-[#0b3866] font-bold shadow-2xs' : 'text-slate-600'
                }`}
                title="Stacked cumulative distribution"
              >
                Stacked
              </button>
            </div>

            {/* Toggle Tabular View */}
            <button
              onClick={() => setShowTable(!showTable)}
              className={`p-1.5 border rounded-xs text-xs font-semibold flex items-center gap-1 cursor-pointer transition-colors ${
                showTable ? 'bg-[#0b3866] text-white border-[#0b3866]' : 'bg-white border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
              title="Toggle accessible data table"
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Table</span>
            </button>
          </div>
        </div>

        {/* Aggregated Quick Metrics Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 pt-3 border-t border-slate-200">
          <div className="p-2.5 bg-white border border-slate-200 rounded-xs flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-bold text-slate-500">Monitored Schemes</div>
              <div className="text-base font-bold text-[#002642] mt-0.5">
                {overallSummary.totalProjects} <span className="text-xs font-normal text-slate-500">Projects</span>
              </div>
            </div>
            <Building2 className="w-5 h-5 text-[#0b3866] opacity-70" />
          </div>

          <div className="p-2.5 bg-amber-50/70 border border-amber-200 rounded-xs flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-bold text-amber-900">Delayed Handover</div>
              <div className="text-base font-bold text-amber-700 mt-0.5">
                {overallSummary.delayed} <span className="text-xs font-normal text-amber-800">({overallSummary.delayedRate}%)</span>
              </div>
            </div>
            <Clock className="w-5 h-5 text-amber-600" />
          </div>

          <div className="p-2.5 bg-emerald-50/70 border border-emerald-200 rounded-xs flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-bold text-emerald-900">On-Track Progress</div>
              <div className="text-base font-bold text-emerald-800 mt-0.5">
                {overallSummary.onTrack} <span className="text-xs font-normal text-emerald-700">({overallSummary.onTrackRate}%)</span>
              </div>
            </div>
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          </div>

          <div className="p-2.5 bg-blue-50/70 border border-blue-200 rounded-xs flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase font-bold text-blue-900">Completed / OC</div>
              <div className="text-base font-bold text-[#0b3866] mt-0.5">
                {overallSummary.completed} <span className="text-xs font-normal text-slate-500">({overallSummary.completedRate}%)</span>
              </div>
            </div>
            <TrendingUp className="w-5 h-5 text-[#0b3866]" />
          </div>
        </div>
      </div>

      {/* Interactive Status Legend & Filter Chips */}
      <div className="px-4 py-2.5 bg-white border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-slate-600 flex items-center gap-1 text-[11px] uppercase tracking-wider">
            <Filter className="w-3 h-3 text-[#0b3866]" />
            Status Filter:
          </span>

          <button
            onClick={() => onSelectStatus && onSelectStatus('ALL')}
            className={`px-2.5 py-1 rounded-xs font-semibold text-xs transition-colors cursor-pointer border ${
              selectedStatus === 'ALL'
                ? 'bg-[#0b3866] text-white border-[#0b3866]'
                : 'bg-slate-50 text-slate-700 border-slate-300 hover:bg-slate-100'
            }`}
          >
            All Statuses ({overallSummary.totalProjects})
          </button>

          {(['ON_TRACK', 'DELAYED', 'COMPLETED', 'LAPSED_DEFAULT'] as ReraPerformanceStatus[]).map(st => {
            const cfg = STATUS_CONFIG[st];
            const isSelected = selectedStatus === st;
            const count = st === 'ON_TRACK' ? overallSummary.onTrack 
              : st === 'DELAYED' ? overallSummary.delayed
              : st === 'COMPLETED' ? overallSummary.completed
              : overallSummary.lapsed;

            return (
              <button
                key={st}
                onClick={() => onSelectStatus && onSelectStatus(isSelected ? 'ALL' : st)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xs font-semibold text-xs border transition-all cursor-pointer ${
                  isSelected 
                    ? 'ring-2 ring-offset-1 ring-slate-700 font-bold shadow-xs' 
                    : 'opacity-85 hover:opacity-100'
                } ${cfg.bgBadge} ${cfg.textBadge} ${cfg.borderBadge}`}
              >
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cfg.color }} />
                <span>{cfg.label}</span>
                <span className="text-[10px] font-mono px-1 py-0.2 rounded-xs bg-white/70">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="text-[11px] text-slate-500 italic hidden md:block">
          *Click any status chip or chart bar to cross-filter parcel records below
        </div>
      </div>

      {/* Main SVG Bar Chart Area */}
      <div className="p-4 sm:p-6 bg-white relative">
        <div className="w-full overflow-x-auto">
          <div className="min-w-[620px]">
            <svg 
              viewBox={`0 0 760 ${chartHeight}`} 
              className="w-full h-auto select-none font-sans"
              style={{ maxHeight: '280px' }}
            >
              {/* Horizontal Grid lines & Y-Axis Ticks */}
              {yTicks.map((tick, i) => {
                const y = getYCoordinate(tick);
                return (
                  <g key={i}>
                    <line 
                      x1={chartPadding.left} 
                      y1={y} 
                      x2={760 - chartPadding.right} 
                      y2={y} 
                      stroke="#e2e8f0" 
                      strokeDasharray={i === 0 ? undefined : "3 3"}
                      strokeWidth={i === 0 ? "1.5" : "1"}
                    />
                    <text 
                      x={chartPadding.left - 8} 
                      y={y + 3.5} 
                      textAnchor="end" 
                      fontSize="9" 
                      fill="#64748b" 
                      fontFamily="monospace"
                      fontWeight="600"
                    >
                      {tick}
                    </text>
                  </g>
                );
              })}

              {/* Y Axis Label */}
              <text
                transform={`rotate(-90)`}
                x={-(chartHeight / 2)}
                y={14}
                textAnchor="middle"
                fontSize="9"
                fontWeight="700"
                fill="#475569"
                letterSpacing="0.05em"
              >
                {metric === 'PROJECT_COUNT' ? 'PROJECT COUNT' : metric === 'LAND_AREA_HA' ? 'OVERLAP AREA (HECTARES)' : 'ALLOTTEES BOUND'}
              </text>

              {/* Zone Bars Rendering */}
              {zoneData.map((zone, zoneIdx) => {
                const availableWidth = 760 - chartPadding.left - chartPadding.right;
                const zoneBandWidth = availableWidth / zoneData.length;
                const zoneCenter = chartPadding.left + zoneBandWidth * zoneIdx + zoneBandWidth / 2;
                const isZoneSelected = selectedZoneId === zone.id;

                const statuses: ReraPerformanceStatus[] = ['ON_TRACK', 'DELAYED', 'COMPLETED', 'LAPSED_DEFAULT'];

                return (
                  <g key={zone.id}>
                    {/* Zone Highlight Background Column */}
                    <rect
                      x={chartPadding.left + zoneBandWidth * zoneIdx + 4}
                      y={chartPadding.top - 10}
                      width={zoneBandWidth - 8}
                      height={chartHeight - chartPadding.top - chartPadding.bottom + 10}
                      fill={isZoneSelected ? '#f0f6fb' : 'transparent'}
                      rx="2"
                      className="hover:fill-slate-50 transition-colors cursor-pointer"
                      onClick={() => onSelectZone && onSelectZone(isZoneSelected ? '' : zone.id)}
                    />

                    {/* Bars Rendering */}
                    {layout === 'GROUPED' ? (
                      // Grouped layout: 4 individual bars side by side per zone
                      (() => {
                        const barWidth = Math.min((zoneBandWidth - 36) / 4, 22);
                        const groupTotalWidth = barWidth * 4 + 3 * 3;
                        const groupStartX = zoneCenter - groupTotalWidth / 2;

                        return statuses.map((st, stIdx) => {
                          const { val, projects } = getStatusValue(zone, st);
                          const cfg = STATUS_CONFIG[st];
                          const barX = groupStartX + stIdx * (barWidth + 3);
                          const barY = getYCoordinate(val);
                          const barHeight = Math.max(getYCoordinate(0) - barY, val > 0 ? 3 : 0);
                          const isBarHovered = hoveredBar?.zoneId === zone.id && hoveredBar?.status === st;
                          const isStatusActive = selectedStatus === 'ALL' || selectedStatus === st;

                          return (
                            <g key={st}>
                              <rect
                                x={barX}
                                y={barY}
                                width={barWidth}
                                height={barHeight}
                                fill={cfg.color}
                                rx="1.5"
                                opacity={isStatusActive ? (isBarHovered ? 1 : 0.9) : 0.25}
                                stroke={isBarHovered ? '#000000' : 'none'}
                                strokeWidth="1.5"
                                className="cursor-pointer transition-all duration-150"
                                onMouseEnter={(e) => {
                                  const rect = e.currentTarget.getBoundingClientRect();
                                  setHoveredBar({
                                    zoneId: zone.id,
                                    status: st,
                                    value: val,
                                    label: `${zone.name} • ${cfg.label}`,
                                    projects,
                                    x: rect.x + rect.width / 2,
                                    y: rect.y - 10,
                                  });
                                }}
                                onMouseLeave={() => setHoveredBar(null)}
                                onClick={() => {
                                  if (onSelectStatus) onSelectStatus(st);
                                  if (onSelectZone) onSelectZone(zone.id);
                                }}
                              />

                              {/* Value Label above bar if > 0 */}
                              {val > 0 && isStatusActive && (
                                <text
                                  x={barX + barWidth / 2}
                                  y={barY - 4}
                                  textAnchor="middle"
                                  fontSize="8.5"
                                  fontWeight="700"
                                  fill="#1e293b"
                                  fontFamily="monospace"
                                >
                                  {metric === 'LAND_AREA_HA' ? val.toFixed(1) : val}
                                </text>
                              )}
                            </g>
                          );
                        });
                      })()
                    ) : (
                      // Stacked Layout: Single composite bar with stacked segments
                      (() => {
                        const barWidth = Math.min(zoneBandWidth - 45, 44);
                        const barX = zoneCenter - barWidth / 2;
                        let currentBottomVal = 0;

                        return statuses.map((st) => {
                          const { val, projects } = getStatusValue(zone, st);
                          if (val === 0) return null;

                          const cfg = STATUS_CONFIG[st];
                          const segBottomY = getYCoordinate(currentBottomVal);
                          const segTopY = getYCoordinate(currentBottomVal + val);
                          const segHeight = Math.max(segBottomY - segTopY, 2);
                          const isBarHovered = hoveredBar?.zoneId === zone.id && hoveredBar?.status === st;
                          const isStatusActive = selectedStatus === 'ALL' || selectedStatus === st;

                          currentBottomVal += val;

                          return (
                            <g key={st}>
                              <rect
                                x={barX}
                                y={segTopY}
                                width={barWidth}
                                height={segHeight}
                                fill={cfg.color}
                                opacity={isStatusActive ? (isBarHovered ? 1 : 0.92) : 0.25}
                                stroke="#ffffff"
                                strokeWidth="1"
                                className="cursor-pointer transition-all"
                                onMouseEnter={(e) => {
                                  const rect = e.currentTarget.getBoundingClientRect();
                                  setHoveredBar({
                                    zoneId: zone.id,
                                    status: st,
                                    value: val,
                                    label: `${zone.name} • ${cfg.label}`,
                                    projects,
                                    x: rect.x + rect.width / 2,
                                    y: rect.y - 10,
                                  });
                                }}
                                onMouseLeave={() => setHoveredBar(null)}
                                onClick={() => {
                                  if (onSelectStatus) onSelectStatus(st);
                                  if (onSelectZone) onSelectZone(zone.id);
                                }}
                              />

                              {/* In-bar label if segment is tall enough */}
                              {segHeight > 14 && isStatusActive && (
                                <text
                                  x={barX + barWidth / 2}
                                  y={segTopY + segHeight / 2 + 3}
                                  textAnchor="middle"
                                  fontSize="8"
                                  fontWeight="700"
                                  fill="#ffffff"
                                  fontFamily="monospace"
                                >
                                  {val}
                                </text>
                              )}
                            </g>
                          );
                        });
                      })()
                    )}

                    {/* X Axis Zone Label & Corridor Badge */}
                    <g 
                      className="cursor-pointer"
                      onClick={() => onSelectZone && onSelectZone(isZoneSelected ? '' : zone.id)}
                    >
                      <text
                        x={zoneCenter}
                        y={chartHeight - chartPadding.bottom + 16}
                        textAnchor="middle"
                        fontSize="9.5"
                        fontWeight={isZoneSelected ? "800" : "700"}
                        fill={isZoneSelected ? "#f37021" : "#002642"}
                      >
                        {zone.zoneName.replace(' Zone', '')}
                      </text>

                      <text
                        x={zoneCenter}
                        y={chartHeight - chartPadding.bottom + 28}
                        textAnchor="middle"
                        fontSize="8"
                        fill="#64748b"
                      >
                        {zone.district} • {zone.totalProjects} Proj
                      </text>
                    </g>
                  </g>
                );
              })}
            </svg>
          </div>
        </div>

        {/* Hover Tooltip Card */}
        {hoveredBar && (
          <div 
            className="absolute z-20 pointer-events-none bg-[#002642] text-white p-3 rounded-xs shadow-xl border border-slate-700 text-xs max-w-xs transition-opacity animate-in fade-in"
            style={{
              left: Math.max(20, Math.min(hoveredBar.x - 120, window.innerWidth - 300)),
              top: 15,
            }}
          >
            <div className="flex items-center justify-between border-b border-slate-700 pb-1.5 mb-1.5">
              <span className="font-bold text-amber-400">{hoveredBar.label}</span>
              <span className="font-mono font-bold text-white bg-white/20 px-1.5 py-0.5 rounded-xs">
                {hoveredBar.value} {metricSuffix}
              </span>
            </div>

            <div className="space-y-1 text-[11px] text-slate-300">
              <div className="font-semibold text-white">Schemes in this category:</div>
              {hoveredBar.projects.length === 0 ? (
                <div className="italic text-slate-400">None in this zone</div>
              ) : (
                <ul className="list-disc list-inside space-y-0.5 text-slate-200">
                  {hoveredBar.projects.map(p => (
                    <li key={p.id} className="truncate">
                      <strong>{p.surveyNumber}:</strong> {p.projectName} ({p.overlappingAreaWithParcelHa} Ha)
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="mt-2 pt-1 border-t border-slate-700/80 text-[10px] text-slate-400">
              Click bar to filter project dossiers below
            </div>
          </div>
        )}
      </div>

      {/* Accessible Zone Aggregate Data Table (Togglable) */}
      {showTable && (
        <div className="border-t border-slate-200 p-4 bg-slate-50/70">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-[#002642] uppercase tracking-wider flex items-center gap-1.5">
              <TableIcon className="w-3.5 h-3.5 text-[#f37021]" />
              <span>Zone Cross-Tabulation Matrix (GIGW &amp; Accessibility Conforming)</span>
            </h4>
            <span className="text-[11px] text-slate-500">Live Cadastral Telemetry</span>
          </div>

          <div className="overflow-x-auto bg-white border border-slate-200 rounded-xs">
            <table className="gov-table">
              <thead>
                <tr>
                  <th>Acquisition Zone</th>
                  <th>Corridor Jurisdiction</th>
                  <th className="text-center">Total Projects</th>
                  <th className="text-center">On-Track</th>
                  <th className="text-center">Delayed</th>
                  <th className="text-center">Completed</th>
                  <th className="text-center">Lapsed/Default</th>
                  <th className="text-right">Land Overlap</th>
                  <th className="text-right">Buyers Affected</th>
                  <th className="text-right">70% Escrow Monitored</th>
                  <th className="text-center">Action</th>
                </tr>
              </thead>
              <tbody>
                {zoneData.map(zone => {
                  const isSelected = selectedZoneId === zone.id;
                  return (
                    <tr 
                      key={zone.zoneId}
                      className={isSelected ? 'bg-blue-50/80 font-semibold' : ''}
                    >
                      <td className="font-bold text-[#0b3866]">
                        {zone.zoneName}
                        <div className="text-[10px] text-slate-500 font-normal">{zone.zoneNameHi}</div>
                      </td>
                      <td className="text-slate-600 text-xs">{zone.majorProjectCorridor}</td>
                      <td className="text-center font-bold font-mono">{zone.totalProjects}</td>
                      <td className="text-center text-emerald-800 font-bold font-mono bg-emerald-50/40">
                        {zone.onTrackCount}
                      </td>
                      <td className="text-center text-amber-800 font-bold font-mono bg-amber-50/40">
                        {zone.delayedCount}
                      </td>
                      <td className="text-center text-[#0b3866] font-bold font-mono bg-blue-50/40">
                        {zone.completedCount}
                      </td>
                      <td className="text-center text-red-800 font-bold font-mono bg-red-50/40">
                        {zone.lapsedCount}
                      </td>
                      <td className="text-right font-mono font-bold text-slate-800">
                        {zone.totalAreaOverlapHa} Ha
                      </td>
                      <td className="text-right font-mono text-[#002642]">
                        {zone.totalAllotteesImpacted} Buyers
                      </td>
                      <td className="text-right font-mono text-emerald-800">
                        {formatCurrencyINR(zone.totalEscrowINR)}
                      </td>
                      <td className="text-center">
                        <button
                          onClick={() => onSelectZone && onSelectZone(isSelected ? '' : zone.zoneId)}
                          className="px-2 py-0.5 text-[11px] font-bold rounded-xs bg-[#0b3866] text-white hover:bg-[#082d52] cursor-pointer"
                        >
                          {isSelected ? 'Viewing' : 'Inspect'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer Navigation Bar */}
      <div className="p-3 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2 text-slate-600">
          <Info className="w-3.5 h-3.5 text-[#0b3866] flex-shrink-0" />
          <span>
            {selectedZoneId 
              ? `Currently isolating records for ${zoneData.find(z => z.zoneId === selectedZoneId)?.zoneName || selectedZoneId}`
              : 'Showing consolidated metrics across all 4 Western Maharashtra acquisition corridors'}
          </span>
        </div>

        {selectedZoneId && (
          <button
            onClick={() => onSelectZone && onSelectZone('')}
            className="text-xs text-blue-800 hover:text-blue-950 font-bold underline cursor-pointer"
          >
            Clear Zone Isolation
          </button>
        )}
      </div>
    </div>
  );
};
