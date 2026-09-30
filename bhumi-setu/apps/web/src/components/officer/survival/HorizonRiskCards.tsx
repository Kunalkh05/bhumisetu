import React from 'react';
import { Clock, AlertTriangle, ShieldCheck } from 'lucide-react';
import { OfficerSurvivalRisk } from '../../../types/survival';

interface HorizonRiskCardsProps {
  riskData: OfficerSurvivalRisk;
  language?: 'en' | 'hi';
}

interface HorizonMetric {
  days: number;
  label: string;
  labelHi: string;
  survivalProb: number;
  eventProb: number;
  isExtrapolated: boolean;
  statutoryContext: string;
}

export const HorizonRiskCards: React.FC<HorizonRiskCardsProps> = ({ riskData, language = 'en' }) => {
  const flags = riskData.extrapolation_status || {};

  const horizons: HorizonMetric[] = [
    {
      days: 30,
      label: '30 Days',
      labelHi: '30 दिन',
      survivalProb: riskData.survival_probability_30d,
      eventProb: riskData.event_probability_30d,
      isExtrapolated: Boolean(flags['30d']),
      statutoryContext: 'Immediate 30-day operational inquiry window',
    },
    {
      days: 90,
      label: '90 Days',
      labelHi: '90 दिन',
      survivalProb: riskData.survival_probability_90d,
      eventProb: riskData.event_probability_90d,
      isExtrapolated: Boolean(flags['90d']),
      statutoryContext: 'Statutory Section 15 objection hearing limit',
    },
    {
      days: 180,
      label: '180 Days',
      labelHi: '180 दिन',
      survivalProb: riskData.survival_probability_180d,
      eventProb: riskData.event_probability_180d,
      isExtrapolated: Boolean(flags['180d'] ?? true),
      statutoryContext: '6-month joint survey & valuation report deadline',
    },
    {
      days: 365,
      label: '365 Days (1 Yr)',
      labelHi: '365 दिन (1 वर्ष)',
      survivalProb: riskData.survival_probability_365d,
      eventProb: riskData.event_probability_365d,
      isExtrapolated: Boolean(flags['365d'] ?? true),
      statutoryContext: 'Section 19 / Section 25 statutory lapse boundary',
    },
    {
      days: 730,
      label: '730 Days (2 Yrs)',
      labelHi: '730 दिन (2 वर्ष)',
      survivalProb: riskData.survival_probability_730d,
      eventProb: riskData.event_probability_730d,
      isExtrapolated: Boolean(flags['730d'] ?? true),
      statutoryContext: 'Maximum statutory project finalization horizon',
    },
  ];

  return (
    <div className="space-y-3" role="region" aria-label="Statutory Horizon Survival Projections">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
          <Clock className="w-4 h-4 text-[#002642]" />
          <span>{language === 'en' ? 'Statutory Horizon Projections' : 'सांविधिक क्षितिज अनुमान'}</span>
        </h4>
        <span className="text-[11px] text-slate-500 font-medium">
          {language === 'en' ? 'Empirical follow-up limit: 148 days' : 'अनुभवजन्य सीमा: 148 दिन'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {horizons.map((h) => {
          const survPct = (h.survivalProb * 100).toFixed(1);
          const eventPct = (h.eventProb * 100).toFixed(1);

          return (
            <div
              key={h.days}
              className={`p-3.5 rounded-xl border transition-all flex flex-col justify-between ${
                h.isExtrapolated
                  ? 'bg-slate-50/70 border-slate-300 border-dashed'
                  : 'bg-white border-slate-200 shadow-xs'
              }`}
            >
              <div>
                <div className="flex items-center justify-between gap-1 mb-2">
                  <span className="text-xs font-bold text-slate-900">
                    {language === 'en' ? h.label : h.labelHi}
                  </span>
                  {h.isExtrapolated ? (
                    <span
                      className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 tracking-tight"
                      title="Statistical extrapolation beyond empirical follow-up window (148 days)"
                    >
                      EXTRAPOLATED
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                      EMPIRICAL
                    </span>
                  )}
                </div>

                <div className="space-y-1.5 pt-1">
                  <div>
                    <span className="text-[10px] font-semibold text-slate-500 block uppercase tracking-wider">
                      {language === 'en' ? 'Survival Prob S(t)' : 'जीवित रहने की संभावना'}
                    </span>
                    <span className="text-xl font-bold font-mono text-slate-900">
                      {survPct}%
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] font-semibold text-slate-500 block uppercase tracking-wider">
                      {language === 'en' ? 'Transition Event P(t)' : 'संक्रमण घटना संभावना'}
                    </span>
                    <span className="text-sm font-semibold font-mono text-[#002642]">
                      {eventPct}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-slate-100">
                <span className="text-[10px] text-slate-500 leading-tight block">
                  {h.statutoryContext}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
