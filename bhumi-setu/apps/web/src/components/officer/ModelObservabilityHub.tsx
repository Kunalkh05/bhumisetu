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
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Top Header */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <BrainCircuit className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
              {language === 'en' ? 'AI Model Performance, Calibration & Drift Hub (Req 18 & 31)' : 'एआई मॉडल प्रदर्शन, कैलिब्रेशन एवं ड्रिफ्ट हब'}
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
              Status: HEALTHY
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en'
              ? 'Realized delay rates vs predicted probabilities, Population Stability Index (PSI) feature drift, and right-censoring logs.'
              : 'वास्तविक विलंब दर बनाम अनुमानित संभावना, फ़ीचर ड्रिफ्ट पीएसआई एवं राइट-सेंसरिंग सांख्यिकी।'}
          </p>
        </div>

        <button
          onClick={handleTriggerRetraining}
          disabled={retrainingRunning}
          className="px-4 py-2 bg-indigo-700 hover:bg-indigo-800 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all disabled:opacity-50"
        >
          <RotateCcw className={`w-3.5 h-3.5 ${retrainingRunning ? 'animate-spin' : ''}`} />
          <span>{retrainingRunning ? 'Training on Point-in-Time Features...' : 'Trigger Model Retraining'}</span>
        </button>
      </div>

      {/* Primary Statistical Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">PR-AUC (Precision-Recall)</span>
          <div className="text-3xl font-black text-slate-900 dark:text-slate-100 font-mono mt-1">
            {modelStats.prAuc.toFixed(3)}
          </div>
          <div className="mt-2 text-xs text-emerald-600 font-semibold flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Lift: +{(modelStats.precisionRecallLift * 100).toFixed(0)}% over Base Rate ({modelStats.evaluationLabelBaseRate})</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">ROC-AUC Score</span>
          <div className="text-3xl font-black text-slate-900 dark:text-slate-100 font-mono mt-1">
            {modelStats.rocAuc.toFixed(3)}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            <span>Threshold required: ≥ 0.75 (Exceeds by +0.11)</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Expected Calibration Error (ECE)</span>
          <div className="text-3xl font-black text-indigo-600 dark:text-indigo-400 font-mono mt-1">
            {modelStats.eceCalibration.toFixed(3)}
          </div>
          <div className="mt-2 text-xs text-emerald-600 font-semibold">
            <span>Passes threshold (≤ 0.05 ECE over 10 bins)</span>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Right-Censored Rows Log (Q1)</span>
          <div className="text-3xl font-black text-slate-900 dark:text-slate-100 font-mono mt-1">
            {modelStats.censoredRowCount} <span className="text-sm font-normal text-slate-500">({(modelStats.censoringRate * 100).toFixed(1)}%)</span>
          </div>
          <div className="mt-2 text-xs text-slate-500">
            <span>Excluded to prevent optimistic leakage bias</span>
          </div>
        </div>
      </div>

      {/* Realized vs Predicted Calibration Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Realized Delay Rate Table */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-blue-700" />
            {language === 'en' ? 'Post-Promotion Realized Delay vs Predicted Probability' : 'वास्तविक विलंब बनाम अनुमानित प्रायिकता'}
          </h3>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-slate-500">
                  <th className="py-2.5 px-3">Risk Band</th>
                  <th className="py-2.5 px-3">Mean Predicted (p̂)</th>
                  <th className="py-2.5 px-3">Realized Delay Rate (ȳ)</th>
                  <th className="py-2.5 px-3">Divergence (|p̂ - ȳ|)</th>
                  <th className="py-2.5 px-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
                <tr>
                  <td className="py-2.5 px-3 font-sans font-bold text-emerald-700">LOW (p &lt; 0.25)</td>
                  <td className="py-2.5 px-3">11.0%</td>
                  <td className="py-2.5 px-3">8.0%</td>
                  <td className="py-2.5 px-3 text-slate-600">0.030</td>
                  <td className="py-2.5 px-3 text-emerald-600 font-sans font-bold">✓ Calibrated</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-sans font-bold text-blue-700">MEDIUM (0.25 - 0.50)</td>
                  <td className="py-2.5 px-3">36.0%</td>
                  <td className="py-2.5 px-3">32.0%</td>
                  <td className="py-2.5 px-3 text-slate-600">0.040</td>
                  <td className="py-2.5 px-3 text-emerald-600 font-sans font-bold">✓ Calibrated</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-sans font-bold text-amber-700">HIGH (0.50 - 0.75)</td>
                  <td className="py-2.5 px-3">62.0%</td>
                  <td className="py-2.5 px-3">64.0%</td>
                  <td className="py-2.5 px-3 text-slate-600">0.020</td>
                  <td className="py-2.5 px-3 text-emerald-600 font-sans font-bold">✓ Calibrated</td>
                </tr>
                <tr>
                  <td className="py-2.5 px-3 font-sans font-bold text-red-700">CRITICAL (p ≥ 0.75)</td>
                  <td className="py-2.5 px-3">84.0%</td>
                  <td className="py-2.5 px-3">88.0%</td>
                  <td className="py-2.5 px-3 text-slate-600">0.040</td>
                  <td className="py-2.5 px-3 text-emerald-600 font-sans font-bold">✓ Calibrated</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Feature Drift (PSI) Monitor */}
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-amber-500" />
              {language === 'en' ? 'Feature Drift (Population Stability Index - PSI)' : 'फ़ीचर ड्रिफ्ट (पीएसआई) निगरानी'}
            </h3>
            <span className="text-[11px] text-slate-500">Cadence: 7 Days</span>
          </div>

          <div className="space-y-3">
            {modelStats.featureDriftPSI.map((item) => (
              <div key={item.featureName} className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 flex justify-between items-center text-xs">
                <div>
                  <span className="font-mono font-bold text-slate-900 dark:text-slate-100 block">
                    {item.featureName}
                  </span>
                  <span className="text-[10px] text-slate-500">Baseline training window vs last 7 days</span>
                </div>

                <div className="text-right">
                  <span className="font-mono font-bold text-slate-800 dark:text-slate-200 text-sm">
                    PSI: {item.psiValue.toFixed(3)}
                  </span>
                  <span className={`block text-[10px] font-bold ${
                    item.status === 'NORMAL' ? 'text-emerald-600' : 'text-amber-600'
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
