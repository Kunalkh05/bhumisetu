import React from 'react';
import { AlertTriangle, AlertCircle, Info, ShieldAlert, Shield } from 'lucide-react';
import { ExtrapolationFlags } from '../../../types/survival';

interface UncertaintyNoticeProps {
  uncertaintyStatus: string;
  calibrationStatus: string;
  extrapolationFlags?: ExtrapolationFlags;
  dataQualityWarning?: string;
  governanceDisclaimer?: string;
  language?: 'en' | 'hi';
}

export const UncertaintyNotice: React.FC<UncertaintyNoticeProps> = ({
  uncertaintyStatus,
  calibrationStatus,
  extrapolationFlags,
  dataQualityWarning,
  governanceDisclaimer,
  language = 'en',
}) => {
  const isHighUncertainty =
    uncertaintyStatus?.includes('HIGH') ||
    uncertaintyStatus?.includes('SPARSE') ||
    uncertaintyStatus?.includes('EXTREME');

  const isZeroEvents =
    uncertaintyStatus?.includes('ZERO_EVENTS') ||
    uncertaintyStatus?.includes('EXTREME');

  const hasExtrapolation = Object.values(extrapolationFlags || {}).some(Boolean);

  return (
    <div className="space-y-3" role="region" aria-label="Statistical Uncertainty & Governance Advisory">
      {/* 1. Event Sparsity / Extreme Uncertainty Banner */}
      {isZeroEvents ? (
        <div className="p-4 rounded-xl bg-amber-500/10 border-2 border-amber-500/40 text-amber-900 flex items-start gap-3 shadow-xs">
          <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-xs uppercase tracking-wider bg-amber-200/60 text-amber-900 px-2 py-0.5 rounded">
                Extreme Statistical Uncertainty (0 Events in Evaluation Cohort)
              </span>
            </div>
            <p className="text-xs leading-relaxed font-medium text-amber-900">
              {language === 'en'
                ? 'Reliable out-of-sample discrimination has not been established for this transition because no target events were observed in the evaluation cohort. Model estimates must be treated as unverified mathematical projections.'
                : 'इस संक्रमण के लिए विश्वसनीय आउट-ऑफ-सैंपल विभेदन स्थापित नहीं किया गया है क्योंकि मूल्यांकन समूह में कोई लक्षित घटना नहीं देखी गई थी।'}
            </p>
          </div>
        </div>
      ) : isHighUncertainty ? (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 text-amber-900 flex items-start gap-3 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-xs uppercase tracking-wider bg-amber-100 text-amber-800 px-2 py-0.5 rounded border border-amber-300">
                High Statistical Uncertainty (Small Sample Size)
              </span>
              <span className="text-[11px] font-mono text-amber-700">EPV &lt; 10</span>
            </div>
            <p className="text-xs leading-relaxed text-amber-900">
              {language === 'en'
                ? 'Limited observed events mean this estimate has substantial statistical uncertainty. Relative hazard estimates carry wide confidence intervals.'
                : 'सीमित देखी गई घटनाओं का अर्थ है कि इस अनुमान में पर्याप्त सांख्यिकीय अनिश्चितता है।'}
            </p>
          </div>
        </div>
      ) : null}

      {/* 2. Uncalibrated / Calibration Status Banner */}
      {calibrationStatus && (
        <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-800 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-slate-600 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="text-xs space-y-0.5">
            <span className="font-semibold text-slate-900">
              {language === 'en' ? 'Calibration Governance: ' : 'कैलिब्रेशन स्थिति: '}
            </span>
            <span className="font-mono text-slate-700">{calibrationStatus}</span>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Empirical calibration was withheld to preserve scientific integrity under small-sample constraints. Raw Cox survival curves $S(t) = S_0(t)^{'{'} \exp(\eta) {'}'}$ are retained as the uncalibrated baseline.
            </p>
          </div>
        </div>
      )}

      {/* 3. Extrapolation Advisory Banner */}
      {hasExtrapolation && (
        <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200 text-blue-900 flex items-start gap-2.5">
          <AlertCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-xs leading-relaxed text-blue-950">
            <strong>{language === 'en' ? 'Extrapolated Horizon Advisory: ' : 'बहिर्वेशित क्षितिज सलाह: '}</strong>
            {language === 'en'
              ? 'Projections beyond 148 days (180d, 365d, 730d) are statistical extrapolations beyond the empirical follow-up ceiling of the evaluation cohort. They are flagged as unvalidated estimates.'
              : '148 दिनों से आगे के अनुमान सांख्यिकीय बहिर्वेशन हैं और इन्हें अनिर्धारित अनुमान माना जाना चाहिए।'}
          </p>
        </div>
      )}

      {/* 4. Statutory Non-Autonomous Governance Disclaimer */}
      {governanceDisclaimer && (
        <div className="p-3 rounded-lg bg-slate-100/90 border border-slate-300 text-slate-700 flex items-start gap-2.5">
          <Shield className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" aria-hidden="true" />
          <p className="text-[11px] leading-relaxed text-slate-600">
            <strong className="text-slate-800 uppercase tracking-wide">
              {language === 'en' ? 'Statutory Governance Notice: ' : 'सांविधिक शासन सूचना: '}
            </strong>
            {governanceDisclaimer}
          </p>
        </div>
      )}
    </div>
  );
};
