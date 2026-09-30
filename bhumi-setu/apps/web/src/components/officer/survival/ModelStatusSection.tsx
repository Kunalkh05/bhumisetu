import React, { useEffect, useState } from 'react';
import { Activity, ShieldCheck, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { SurvivalMLHealth } from '../../../types/survival';
import { survivalRiskService } from '../../../services/survivalRiskService';

interface ModelStatusSectionProps {
  language?: 'en' | 'hi';
}

export const ModelStatusSection: React.FC<ModelStatusSectionProps> = ({ language = 'en' }) => {
  const [health, setHealth] = useState<SurvivalMLHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await survivalRiskService.getSurvivalMLHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err?.message || 'Unable to connect to ML health service');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="gov-surface-card p-5 space-y-4" role="region" aria-label="Survival ML Subsystem Health and Verification">
      <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#002642]" />
          <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
            {language === 'en' ? 'Survival ML Engine Status & Provenance' : 'उत्तरजीविता एमएल इंजन स्थिति'}
          </h4>
          <span
            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
              health?.status === 'healthy'
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-amber-50 text-amber-700 border-amber-200'
            }`}
          >
            {health?.status ? health.status.toUpperCase() : 'CHECKING...'}
          </span>
        </div>

        <button
          onClick={fetchHealth}
          disabled={loading}
          className="p-1 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 text-xs flex items-center gap-1 cursor-pointer disabled:opacity-50"
          title="Refresh health status"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          <span className="text-[11px] font-medium">Refresh</span>
        </button>
      </div>

      {error ? (
        <div className="p-3 bg-red-50 text-red-800 text-xs rounded-lg border border-red-200 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      ) : health ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Model Version */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
              Model Specification
            </span>
            <span className="text-xs font-mono font-bold text-slate-900 mt-0.5 block truncate" title={health.model_version}>
              {health.model_version}
            </span>
            <span className="text-[10px] text-emerald-700 font-medium flex items-center gap-1 mt-1">
              <CheckCircle2 className="w-3 h-3" /> Cox Proportional Hazards
            </span>
          </div>

          {/* Feature Version */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
              Feature Contract
            </span>
            <span className="text-xs font-mono font-bold text-slate-900 mt-0.5 block truncate" title={health.feature_version}>
              {health.feature_version}
            </span>
            <span className="text-[10px] text-slate-500 font-medium block mt-1">
              15 Purged Clean Predictors
            </span>
          </div>

          {/* Supported Transitions */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
              Statutory Transitions
            </span>
            <span className="text-xs font-mono font-bold text-slate-900 mt-0.5 block">
              {health.available_transitions?.length || 0} Statutory Horizons
            </span>
            <span className="text-[10px] text-slate-500 font-medium block mt-1">
              Sec 11 &rarr; 19 &bull; Sec 19 &rarr; Award &bull; Milestone
            </span>
          </div>

          {/* Explainability Subsystem */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold block">
              Explainability Subsystem
            </span>
            <span className="text-xs font-mono font-bold text-emerald-800 mt-0.5 block">
              Auditable Decomposition Active
            </span>
            <span className="text-[10px] text-slate-500 font-medium block mt-1">
              Zero-leakage point-in-time
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
};
