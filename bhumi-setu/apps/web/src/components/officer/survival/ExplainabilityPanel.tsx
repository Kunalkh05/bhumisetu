import React from 'react';
import { TrendingUp, TrendingDown, HelpCircle, AlertCircle, FileSearch, ShieldCheck } from 'lucide-react';
import { OfficerSurvivalExplanation, HazardFactorContribution } from '../../../types/survival';

interface ExplainabilityPanelProps {
  explanation: OfficerSurvivalExplanation | null;
  loading?: boolean;
  language?: 'en' | 'hi';
}

export const ExplainabilityPanel: React.FC<ExplainabilityPanelProps> = ({
  explanation,
  loading = false,
  language = 'en',
}) => {
  if (loading) {
    return (
      <div className="gov-surface-card p-6 flex flex-col items-center justify-center space-y-2 text-center">
        <div className="w-6 h-6 border-2 border-[#002642] border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-500 font-medium">
          {language === 'en' ? 'Decomposing Cox log-hazard factor contributions...' : 'कॉक्स लॉग-हैज़र्ड योगदानों का विश्लेषण जारी...'}
        </p>
      </div>
    );
  }

  if (!explanation) {
    return (
      <div className="gov-surface-card p-6 text-center text-slate-500 text-xs">
        {language === 'en'
          ? 'No explanation available for this case snapshot.'
          : 'इस केस स्नैपशॉट के लिए कोई व्याख्या उपलब्ध नहीं है।'}
      </div>
    );
  }

  const higherFactors = explanation.why_hazard_is_higher || [];
  const lowerFactors = explanation.why_hazard_is_lower || [];
  const missingFeatures = explanation.missing_features || [];

  return (
    <div className="gov-surface-card p-5 space-y-5" role="region" aria-label="Auditable Survival Risk Factor Contributions">
      {/* Header */}
      <div className="border-b border-slate-100 pb-3 flex justify-between items-start flex-wrap gap-2">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#002642]" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
              {language === 'en'
                ? 'Auditable Survival Risk Explanation (Cox Proportional Hazards)'
                : 'ऑडिट-योग्य उत्तरजीविता जोखिम व्याख्या'}
            </h3>
            <span className="text-[10px] font-bold px-2 py-0.5 bg-blue-50 text-blue-800 rounded border border-blue-200">
              Additive Decomposition
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1 leading-relaxed">
            {explanation.summary_narrative}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5 font-medium">
            Strict Non-Causal Policy: Feature associations describe statistical model correlation relative to the baseline cohort, not administrative causation.
          </p>
        </div>

        <div className="text-right">
          <span className="text-xs font-mono font-bold text-slate-700 bg-slate-50 px-2 py-1 rounded border border-slate-200 block">
            Linear Predictor (&eta;): {explanation.linear_predictor.toFixed(4)}
          </span>
          <span className="text-[10px] text-slate-500 mt-0.5 block">
            Relative Hazard: <strong>{explanation.relative_hazard.toFixed(3)}x</strong>
          </span>
        </div>
      </div>

      {/* Two-Column Factor Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Factors Increasing Estimated Hazard */}
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 pb-1 border-b border-amber-100">
            <TrendingUp className="w-3.5 h-3.5 text-amber-600" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {language === 'en' ? 'Factors Increasing Estimated Hazard' : 'अनुमानित जोखिम बढ़ाने वाले कारक'}
            </h4>
            <span className="text-[10px] font-mono text-slate-500 ml-auto">
              ({higherFactors.length})
            </span>
          </div>

          {higherFactors.length === 0 ? (
            <p className="text-xs text-slate-400 italic p-3 bg-slate-50 rounded-lg">
              No positive contributors identified relative to baseline cohort.
            </p>
          ) : (
            <div className="space-y-2.5">
              {higherFactors.map((f, idx) => (
                <div
                  key={f.feature || f.feature_name || idx}
                  className="p-3 rounded-lg border border-amber-200/70 bg-amber-50/30 space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs gap-2">
                    <span className="font-bold text-slate-900 leading-tight">
                      {f.label || f.human_name || f.feature || f.feature_name}
                    </span>
                    <span className="font-mono text-amber-900 font-bold text-[11px] shrink-0 bg-amber-100/80 px-1.5 py-0.5 rounded">
                      +{f.contribution.toFixed(4)} log-hazard
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-600">
                    <span>
                      Observed: <strong className="font-mono">{String(f.value ?? f.feature_value ?? 'N/A')}</strong>
                    </span>
                    <span className="font-mono text-slate-700">
                      Multiplier: <strong>{f.hazard_multiplier.toFixed(3)}x</strong>
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-snug">
                    {f.narrative || `The model associates this factor with an increased hazard contribution of +${f.contribution.toFixed(4)}.`}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Factors Decreasing Estimated Hazard */}
        <div className="space-y-3">
          <div className="flex items-center gap-1.5 pb-1 border-b border-emerald-100">
            <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
              {language === 'en' ? 'Factors Decreasing Estimated Hazard' : 'अनुमानित जोखिम घटाने वाले कारक'}
            </h4>
            <span className="text-[10px] font-mono text-slate-500 ml-auto">
              ({lowerFactors.length})
            </span>
          </div>

          {lowerFactors.length === 0 ? (
            <p className="text-xs text-slate-400 italic p-3 bg-slate-50 rounded-lg">
              No negative contributors identified relative to baseline cohort.
            </p>
          ) : (
            <div className="space-y-2.5">
              {lowerFactors.map((f, idx) => (
                <div
                  key={f.feature || f.feature_name || idx}
                  className="p-3 rounded-lg border border-emerald-200/70 bg-emerald-50/30 space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs gap-2">
                    <span className="font-bold text-slate-900 leading-tight">
                      {f.label || f.human_name || f.feature || f.feature_name}
                    </span>
                    <span className="font-mono text-emerald-900 font-bold text-[11px] shrink-0 bg-emerald-100/80 px-1.5 py-0.5 rounded">
                      {f.contribution.toFixed(4)} log-hazard
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-600">
                    <span>
                      Observed: <strong className="font-mono">{String(f.value ?? f.feature_value ?? 'N/A')}</strong>
                    </span>
                    <span className="font-mono text-slate-700">
                      Multiplier: <strong>{f.hazard_multiplier.toFixed(3)}x</strong>
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 leading-snug">
                    {f.narrative || `The model associates this factor with a decreased hazard contribution of ${f.contribution.toFixed(4)}.`}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Missing Feature Audit Section (STEP 8 of LOOP 10) */}
      {missingFeatures.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-100">
          <div className="flex items-center gap-1.5 mb-2">
            <FileSearch className="w-3.5 h-3.5 text-slate-500" />
            <h5 className="text-[11px] font-bold text-slate-700 uppercase tracking-wider">
              {language === 'en' ? 'Unavailable / Missing Features at Snapshot Date' : 'स्नैपशॉट तिथि पर अनुपलब्ध फ़ीचर'}
            </h5>
          </div>
          <div className="flex flex-wrap gap-2">
            {missingFeatures.map((m, idx) => (
              <span
                key={m.feature || m.feature_name || idx}
                className="text-[10px] px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-600 font-mono"
              >
                {m.label || m.human_name || m.feature || m.feature_name} ({m.imputation || m.status || 'unobserved'})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
