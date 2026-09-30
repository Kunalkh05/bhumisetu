import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  Activity, 
  TrendingUp, 
  AlertCircle, 
  CheckCircle2, 
  ShieldCheck, 
  RotateCcw, 
  Sparkles,
  BarChart2,
  LineChart,
  BrainCircuit,
  Info
} from 'lucide-react';
import { MOCK_MODEL_STATS } from '../../data/mockData';

export const ModelObservabilityHub: React.FC = () => {
  const { modelStats, language, addToast } = useApp();
  const [retrainingRunning, setRetrainingRunning] = useState(false);

  const handleTriggerRetraining = () => {
    setRetrainingRunning(true);
    setTimeout(() => {
      setRetrainingRunning(false);
      addToast({
        type: 'success',
        message: 'Model retraining run completed. PR-AUC improved to 0.798, ECE reduced to 0.031. Promoted as v2.5.',
        messageHi: 'मॉडल पुनःप्रशिक्षण पूर्ण। नया संस्करण v2.5 सक्रिय।',
      });
    }, 2000);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-5 animate-in fade-in">
      {/* Top Header */}
      <div className="gov-surface-card p-5 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-[#002642]" />
              <span>{language === 'en' ? 'AI Model Performance, Calibration & Drift Hub' : 'एआई मॉडल प्रदर्शन, कैलिब्रेशन एवं ड्रिफ्ट हब'}</span>
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
              HEALTHY • CALIBRATED
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {language === 'en'
              ? 'Realized delay rates vs predicted probabilities, Population Stability Index (PSI) feature drift, and right-censoring logs.'
              : 'वास्तविक विलंब दर बनाम अनुमानित संभावना, फ़ीचर ड्रिफ्ट पीएसआई एवं राइट-सेंसरिंग सांख्यिकी।'}
          </p>
        </div>

        <button
          onClick={handleTriggerRetraining}
          disabled={retrainingRunning}
          className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-xs transition-all disabled:opacity-50 cursor-pointer"
        >
          <RotateCcw className={`w-3.5 h-3.5 ${retrainingRunning ? 'animate-spin' : ''}`} />
          <span>{retrainingRunning ? 'Training on Point-in-Time Features...' : 'Trigger Model Retraining'}</span>
        </button>
      </div>

      {/* Primary Statistical Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">PR-AUC Score</span>
            <div className="text-3xl font-black text-slate-900 font-mono mt-1">
              {modelStats.prAuc.toFixed(3)}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-emerald-700 font-medium flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>+{(modelStats.precisionRecallLift * 100).toFixed(0)}% Lift over Base Rate ({modelStats.evaluationLabelBaseRate})</span>
          </div>
        </div>

        <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">ROC-AUC Score</span>
            <div className="text-3xl font-black text-slate-900 font-mono mt-1">
              {modelStats.rocAuc.toFixed(3)}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
            <span>Threshold required: ≥ 0.75 (Exceeds by +0.11)</span>
          </div>
        </div>

        <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Expected Calibration (ECE)</span>
            <div className="text-3xl font-black text-[#002642] font-mono mt-1">
              {modelStats.eceCalibration.toFixed(3)}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-emerald-700 font-medium">
            <span>Passes threshold (≤ 0.05 ECE over 10 bins)</span>
          </div>
        </div>

        <div className="gov-surface-card p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Right-Censored Rows (Q1)</span>
            <div className="text-3xl font-black text-slate-900 font-mono mt-1">
              {modelStats.censoredRowCount} <span className="text-xs font-normal text-slate-500">({(modelStats.censoringRate * 100).toFixed(1)}%)</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
            <span>Excluded to prevent optimistic leakage bias</span>
          </div>
        </div>
      </div>

      {/* Realized vs Predicted Calibration Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Realized Delay Rate Table */}
        <div className="gov-surface-card p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-[#002642]" />
              <span>{language === 'en' ? 'Post-Promotion Realized Delay vs Predicted Probability' : 'वास्तविक विलंब बनाम अनुमानित प्रायिकता'}</span>
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">Empirical validation of model calibration across 10 probability bins</p>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="gov-table-2026">
              <thead>
                <tr>
                  <th>Risk Band</th>
                  <th>Mean Predicted (p̂)</th>
                  <th>Realized Delay Rate (ȳ)</th>
                  <th>Divergence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody className="font-mono text-xs">
                <tr>
                  <td className="font-sans font-bold text-emerald-700">LOW (p &lt; 0.25)</td>
                  <td>11.0%</td>
                  <td>8.0%</td>
                  <td className="text-slate-600">0.030</td>
                  <td className="font-sans font-bold text-emerald-700">✓ Calibrated</td>
                </tr>
                <tr>
                  <td className="font-sans font-bold text-blue-700">MEDIUM (0.25 - 0.50)</td>
                  <td>36.0%</td>
                  <td>32.0%</td>
                  <td className="text-slate-600">0.040</td>
                  <td className="font-sans font-bold text-emerald-700">✓ Calibrated</td>
                </tr>
                <tr>
                  <td className="font-sans font-bold text-amber-700">HIGH (0.50 - 0.75)</td>
                  <td>62.0%</td>
                  <td>64.0%</td>
                  <td className="text-slate-600">0.020</td>
                  <td className="font-sans font-bold text-emerald-700">✓ Calibrated</td>
                </tr>
                <tr>
                  <td className="font-sans font-bold text-red-700">CRITICAL (p ≥ 0.75)</td>
                  <td>84.0%</td>
                  <td>88.0%</td>
                  <td className="text-slate-600">0.040</td>
                  <td className="font-sans font-bold text-emerald-700">✓ Calibrated</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Feature Drift (PSI) Monitor */}
        <div className="gov-surface-card p-5 space-y-4">
          <div className="border-b border-slate-100 pb-3 flex justify-between items-center">
            <div>
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-amber-500" />
                <span>{language === 'en' ? 'Feature Drift (Population Stability Index - PSI)' : 'फ़ीचर ड्रिफ्ट (पीएसआई) निगरानी'}</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">Automated detection of covariate shifts</p>
            </div>
            <span className="text-[11px] text-slate-400 font-mono">Cadence: 7d</span>
          </div>

          <div className="space-y-2.5">
            {modelStats.featureDriftPSI.map((item) => (
              <div key={item.featureName} className="p-3 rounded-lg bg-slate-50/70 border border-slate-200 flex justify-between items-center text-xs">
                <div>
                  <span className="font-mono font-bold text-slate-900 block">
                    {item.featureName}
                  </span>
                  <span className="text-[11px] text-slate-500">Baseline training window vs last 7 days</span>
                </div>

                <div className="text-right">
                  <span className="font-mono font-bold text-slate-900 text-sm">
                    PSI: {item.psiValue.toFixed(3)}
                  </span>
                  <span className={`block text-[10px] font-bold ${
                    item.status === 'NORMAL' ? 'text-emerald-700' : 'text-amber-700'
                  }`}>
                    {item.status} (&lt; 0.20 Threshold)
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
