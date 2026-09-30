import React, { useEffect, useState } from 'react';
import { 
  ShieldAlert, 
  Clock, 
  Activity, 
  HelpCircle, 
  AlertTriangle, 
  Calendar, 
  Compass, 
  Layers, 
  TrendingUp, 
  FileText,
  RefreshCw,
  Lock,
  ChevronRight
} from 'lucide-react';
import { useApp } from '../../../context/AppContext';
import { 
  OfficerSurvivalExplanation, 
  OfficerSurvivalRisk, 
  StatutoryTransition 
} from '../../../types/survival';
import { survivalRiskService, ApiErrorResult } from '../../../services/survivalRiskService';
import { UncertaintyNotice } from './UncertaintyNotice';
import { HorizonRiskCards } from './HorizonRiskCards';
import { SurvivalCurveChart } from './SurvivalCurveChart';
import { ExplainabilityPanel } from './ExplainabilityPanel';
import { ModelStatusSection } from './ModelStatusSection';

interface SurvivalRiskDashboardProps {
  caseId: string | number;
  currentStageName?: string;
  onNavigateToTimeline?: () => void;
}

export const SurvivalRiskDashboard: React.FC<SurvivalRiskDashboardProps> = ({
  caseId,
  currentStageName = 'SECTION_11',
  onNavigateToTimeline,
}) => {
  const { currentUser, language } = useApp();
  const [transition, setTransition] = useState<StatutoryTransition>('SECTION_11_TO_SECTION_19');
  const [snapshotDate, setSnapshotDate] = useState<string>(new Date().toISOString().split('T')[0]);

  const [riskData, setRiskData] = useState<OfficerSurvivalRisk | null>(null);
  const [explanationData, setExplanationData] = useState<OfficerSurvivalExplanation | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ApiErrorResult | null>(null);

  // Check role authorization (STEP 12)
  const isOfficer = currentUser.role !== 'CITIZEN';

  const loadRiskAnalytics = async () => {
    if (!isOfficer) return;
    setLoading(true);
    setError(null);

    try {
      // Parallel fetch for risk projection and auditable explanation
      const [riskRes, explRes] = await Promise.all([
        survivalRiskService.getCaseSurvivalRisk(caseId, transition, snapshotDate),
        survivalRiskService.getCaseSurvivalExplanation(caseId, transition, snapshotDate),
      ]);

      setRiskData(riskRes);
      setExplanationData(explRes);
    } catch (err: any) {
      setError({
        code: err?.code || 'FETCH_FAILED',
        message: err?.message || 'Failed to load survival risk analytics from the backend API.',
        statusCode: err?.statusCode || 500,
        details: err?.details,
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRiskAnalytics();
  }, [caseId, transition, snapshotDate, isOfficer]);

  // Unauthorized view state
  if (!isOfficer) {
    return (
      <div className="gov-surface-card p-8 text-center space-y-3" role="alert">
        <Lock className="w-8 h-8 text-slate-400 mx-auto" />
        <h3 className="text-sm font-bold text-slate-900 uppercase">
          {language === 'en' ? 'Unauthorized Access' : 'अनधिकृत पहुंच'}
        </h3>
        <p className="text-xs text-slate-600 max-w-md mx-auto">
          {language === 'en'
            ? 'Survival risk analysis is an internal administrative decision-support tool restricted to authorized government officers.'
            : 'उत्तरजीविता जोखिम विश्लेषण केवल अधिकृत सरकारी अधिकारियों के लिए प्रतिबंधित है।'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-5 animate-in fade-in" role="main" aria-label="Officer Survival Risk & Explainability Dashboard">
      {/* Top Control Bar: Case Info, Transition Selector, and Refresh */}
      <div className="gov-surface-card p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4 border-l-4 border-l-[#002642]">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-mono font-bold bg-[#002642] text-white px-2 py-0.5 rounded">
              CASE: {String(caseId)}
            </span>
            <span className="text-[10px] font-bold bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-200">
              STAGE: {currentStageName.replace(/_/g, ' ')}
            </span>
            <span className="text-[10px] font-mono text-slate-500">
              SNAPSHOT: {snapshotDate}
            </span>
          </div>
          <h2 className="text-base sm:text-lg font-bold text-slate-900 tracking-tight">
            {language === 'en'
              ? 'Statutory Survival Risk & Transition Probability Engine'
              : 'सांविधिक उत्तरजीविता जोखिम एवं संक्रमण इंजन'}
          </h2>
          <p className="text-xs text-slate-500">
            {language === 'en'
              ? 'Parametric Cox regression estimating statutory milestone completion dynamics and point-in-time hazard contributions.'
              : 'सांविधिक मील के पत्थर पूरा होने की गतिशीलता का अनुमान लगाने वाला कॉक्स प्रतिगमन।'}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Transition Selector (STEP 11) */}
          <div className="flex flex-col">
            <label htmlFor="transition-select" className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">
              Statutory Transition
            </label>
            <select
              id="transition-select"
              value={transition}
              onChange={(e) => setTransition(e.target.value as StatutoryTransition)}
              aria-label="Select statutory milestone transition"
              className="px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-xs font-semibold text-slate-900 focus:outline-hidden focus:ring-1 focus:ring-[#002642] cursor-pointer"
            >
              <option value="SECTION_11_TO_SECTION_19">Section 11 &rarr; Section 19 Declaration</option>
              <option value="SECTION_19_TO_AWARD">Section 19 &rarr; Final Compensation Award</option>
              <option value="CASE_INITIATION_TO_MILESTONE">Proceeding Initiation &rarr; Statutory Milestone</option>
            </select>
          </div>

          {/* Refresh button */}
          <button
            onClick={loadRiskAnalytics}
            disabled={loading}
            aria-label="Refresh survival risk analysis"
            className="mt-3.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Refresh analysis"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Loading State (STEP 11) */}
      {loading && (
        <div className="gov-surface-card p-12 text-center space-y-3" role="status">
          <div className="w-8 h-8 border-3 border-[#002642] border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs font-bold text-slate-700">Calculating survival risk...</p>
          <p className="text-[11px] text-slate-500">
            Evaluating point-in-time feature vector against Cox baseline survival baseline $S_0(t)$...
          </p>
        </div>
      )}

      {/* Error / Missing Data States (STEP 11) */}
      {!loading && error && (
        <div className="gov-surface-card p-6 border-l-4 border-l-red-500 space-y-3" role="alert">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600 shrink-0" />
            <h3 className="text-sm font-bold text-slate-900">
              {error.code === 'VALIDATION_FAILED'
                ? 'Risk Estimate Unavailable: Required Point-in-Time Data Missing'
                : 'Risk Model Currently Unavailable'}
            </h3>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {error.message}
          </p>
          {error.details && (
            <pre className="p-3 bg-slate-50 rounded text-[11px] text-slate-700 font-mono overflow-x-auto border border-slate-200">
              {JSON.stringify(error.details, null, 2)}
            </pre>
          )}
        </div>
      )}

      {/* Zero-Event Transition Warning (STEP 11 & STEP 6) */}
      {!loading && !error && transition === 'SECTION_19_TO_AWARD' && (
        <div className="p-4 bg-amber-500/10 border-2 border-amber-500/40 rounded-xl text-amber-950 space-y-1">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
            <span className="text-xs font-bold uppercase tracking-wider">
              Zero-Event Transition Warning (Holdout Limitation)
            </span>
          </div>
          <p className="text-xs leading-relaxed">
            Reliable out-of-sample discrimination has not been established for this transition because no target events were observed in the evaluation cohort.
            Treat relative hazard estimates with extreme administrative caution.
          </p>
        </div>
      )}

      {/* Content Rendered on Success */}
      {!loading && !error && riskData && (
        <>
          {/* Prominent Distinction: RELATIVE HAZARD vs EVENT PROBABILITY (STEP 3 & STEP 5) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Metric 1: Relative Hazard (NOT A PROBABILITY!) */}
            <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between border-t-4 border-t-[#002642]">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Relative Hazard (Ratio)
                  </span>
                  <span className="text-[10px] font-semibold text-slate-400">
                    Baseline: 1.00x
                  </span>
                </div>
                <div className="text-2xl sm:text-3xl font-black font-mono text-slate-900 mt-1">
                  {riskData.relative_hazard.toFixed(3)}x
                </div>
                <span className="text-[11px] font-medium text-slate-600 block mt-1">
                  {riskData.relative_hazard < 1.0
                    ? `${((1 - riskData.relative_hazard) * 100).toFixed(0)}% lower hazard than reference cohort`
                    : `${((riskData.relative_hazard - 1) * 100).toFixed(0)}% higher hazard than reference cohort`}
                </span>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 text-[10px] text-slate-500 leading-tight">
                <strong>Important:</strong> Relative hazard is a proportional intensity ratio ($\exp(\eta)$), <em>not</em> an event probability.
              </div>
            </div>

            {/* Metric 2: 90-Day Transition Event Probability */}
            <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between border-t-4 border-t-emerald-600">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    90-Day Transition Probability
                  </span>
                  <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded">
                    P(Event by 90d)
                  </span>
                </div>
                <div className="text-2xl sm:text-3xl font-black font-mono text-[#002642] mt-1">
                  {(riskData.event_probability_90d * 100).toFixed(2)}%
                </div>
                <span className="text-[11px] font-medium text-slate-600 block mt-1">
                  Survival probability S(90d): {(riskData.survival_probability_90d * 100).toFixed(1)}%
                </span>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 text-[10px] text-slate-500 leading-tight">
                Probability of completing transition within statutory Section 15 objection window.
              </div>
            </div>

            {/* Metric 3: Advisory Operational Risk Band */}
            <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between border-t-4 border-t-amber-500">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    Advisory Risk Classification
                  </span>
                  <span className="text-[10px] font-mono text-slate-400">
                    Decision Support Only
                  </span>
                </div>
                <div className="text-lg sm:text-xl font-bold font-mono text-slate-900 mt-2 truncate" title={riskData.risk_band_90d}>
                  {riskData.risk_band_90d}
                </div>
                <span className="text-[11px] text-amber-800 font-medium block mt-1">
                  Requires independent officer verification.
                </span>
              </div>
              <div className="mt-3 pt-2.5 border-t border-slate-100 text-[10px] text-slate-500 leading-tight">
                Model Version: <span className="font-mono">{riskData.model_version}</span>
              </div>
            </div>
          </div>

          {/* Uncertainty Notice (STEP 6) */}
          <UncertaintyNotice
            uncertaintyStatus={riskData.uncertainty_status}
            calibrationStatus={riskData.calibration_status}
            extrapolationFlags={riskData.extrapolation_status}
            dataQualityWarning={riskData.data_quality_warning}
            governanceDisclaimer={riskData.governance_disclaimer}
            language={language}
          />

          {/* Horizon Risk Cards (STEP 4) */}
          <HorizonRiskCards riskData={riskData} language={language} />

          {/* Survival Curve Chart (STEP 5) */}
          <SurvivalCurveChart riskData={riskData} language={language} />

          {/* Explainability Panel (STEP 7 & STEP 8) */}
          <ExplainabilityPanel
            explanation={explanationData}
            language={language}
          />

          {/* Case Timeline Context (STEP 9) */}
          <div className="gov-surface-card p-5 space-y-3">
            <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-100 pb-2">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-[#002642]" />
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  {language === 'en' ? 'Point-in-Time Case Progression' : 'केस प्रगति समयरेखा'}
                </h4>
              </div>
              {onNavigateToTimeline && (
                <button
                  onClick={onNavigateToTimeline}
                  className="text-xs font-semibold text-[#002642] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <span>View Full Event Log</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <p className="text-xs text-slate-600 leading-relaxed">
              Predictions were computed strictly as of snapshot date <strong className="font-mono">{snapshotDate}</strong>.
              Information effective after this timestamp was excluded by construction to prevent future leakage.
            </p>
          </div>

          {/* Model Status Section (STEP 10) */}
          <ModelStatusSection language={language} />
        </>
      )}
    </div>
  );
};
