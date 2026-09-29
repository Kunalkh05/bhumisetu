import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  AlertTriangle, 
  Clock, 
  FileWarning, 
  HelpCircle, 
  CheckCircle2, 
  IndianRupee, 
  TrendingUp, 
  MapPin, 
  Layers, 
  ShieldAlert, 
  ArrowUpRight,
  Filter,
  BarChart3,
  Calendar,
  Building,
  FileText
} from 'lucide-react';
import { formatCurrencyINR, formatDate } from '../../lib/utils';
import { CaseStage, RiskBand } from '../../types';
import { NationalEmblem } from '../common/NationalEmblem';
import { GovSchemeLeaderboardBanner } from '../common/GovSchemeBanners';
import { GigwSchemeScrollBanner } from '../common/GigwSchemeScrollBanner';

export const OfficerDashboard: React.FC<{ onNavigateToCase: (caseId: string) => void }> = ({ onNavigateToCase }) => {
  const { cases, currentUser, language, setSelectedCaseId } = useApp();
  const [selectedJurisdiction, setSelectedJurisdiction] = useState<string>('ALL');

  // Filter cases by jurisdiction
  const filteredCases = cases.filter(c => {
    if (selectedJurisdiction !== 'ALL' && c.tehsil !== selectedJurisdiction && c.district !== selectedJurisdiction) {
      return false;
    }
    return currentUser.jurisdiction.includes(c.district) || currentUser.jurisdiction.includes(c.tehsil);
  });

  // Calculate Metrics
  const totalCases = filteredCases.length;
  const criticalCases = filteredCases.filter(c => c.riskBand === 'CRITICAL').length;
  const highRiskCases = filteredCases.filter(c => c.riskBand === 'HIGH').length;
  const mediumRiskCases = filteredCases.filter(c => c.riskBand === 'MEDIUM').length;
  const lowRiskCases = filteredCases.filter(c => c.riskBand === 'LOW').length;

  const breachedDeadlines = filteredCases.filter(c => c.isBreached || c.daysRemaining < 0).length;
  const approachingDeadlines = filteredCases.filter(c => !c.isBreached && c.daysRemaining >= 0 && c.daysRemaining <= 15).length;

  const totalOpenBlockingIssues = filteredCases.reduce((sum, c) => 
    sum + c.validationIssues.filter(v => v.severity === 'BLOCKING' && v.resolutionState === 'OPEN').length, 0
  );
  const totalOpenMajorIssues = filteredCases.reduce((sum, c) => 
    sum + c.validationIssues.filter(v => v.severity === 'MAJOR' && v.resolutionState === 'OPEN').length, 0
  );

  const totalUndisposedObjections = filteredCases.reduce((sum, c) => 
    sum + c.objections.filter(o => o.disposalState === 'PENDING').length, 0
  );

  const totalAwarded = filteredCases.reduce((sum, c) => sum + c.totalAwardedAmount, 0);
  const totalDisbursed = filteredCases.reduce((sum, c) => sum + c.totalDisbursedAmount, 0);
  const disbursementRate = totalAwarded > 0 ? Math.round((totalDisbursed / totalAwarded) * 100) : 0;

  // Stages count breakdown
  const stagesList: { stage: CaseStage; label: string; labelHi: string }[] = [
    { stage: 'STAGE_1_SIA', label: 'Section 4 SIA Report', labelHi: 'धारा 4 सामाजिक प्रभाव' },
    { stage: 'STAGE_2_PRELIM_NOTIF', label: 'Section 11 Preliminary Notif', labelHi: 'धारा 11 प्रारंभिक अधिसूचना' },
    { stage: 'STAGE_3_OBJECTIONS', label: 'Section 15 Hearing & Objections', labelHi: 'धारा 15 सुनवाई व आपत्तियां' },
    { stage: 'STAGE_4_DECLARATION', label: 'Section 19 Declaration', labelHi: 'धारा 19 अंतिम घोषणा' },
    { stage: 'STAGE_5_AWARD_COMPENSATION', label: 'Section 23 Award Determination', labelHi: 'धारा 23 पंचाट निर्धारण' },
    { stage: 'STAGE_6_DISBURSEMENT', label: 'Section 38 Payout & Possession', labelHi: 'धारा 38 भुगतान व कब्जा' },
  ];

  return (
    <div className="space-y-4">
      {/* Top Banner with Officer Details & Jurisdiction Selector */}
      <div className="bg-white border border-slate-300 shadow-xs">
        <div className="tiranga-strip"></div>
        <div className="p-4 border-l-4 border-l-[#002b49] flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex flex-col items-center justify-center p-1 bg-slate-50 border border-slate-300 shadow-2xs">
              <NationalEmblem size={32} color="#002b49" showSlogan={false} />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 text-[10px] font-bold bg-[#002b49] text-white uppercase">
                  {currentUser.role.replace('_', ' ')}
                </span>
                <span className="text-xs text-slate-500 font-medium">
                  {language === 'en' ? 'Competent Authority for Land Acquisition (CALA)' : 'सक्षम प्राधिकारी (भू-अधिग्रहण)'}
                </span>
              </div>
              <h2 className="text-lg font-bold text-[#002b49]">
                {language === 'en' ? `Officer Workspace: ${currentUser.name}` : `अधिकारी कार्यक्षेत्र: ${currentUser.nameHi}`}
              </h2>
              <p className="text-xs text-slate-600">
                {language === 'en' ? currentUser.designation : currentUser.designationHi} • {language === 'en' ? 'Jurisdiction:' : 'अधिकार क्षेत्र:'} <strong>{currentUser.jurisdiction.join(', ')}</strong>
              </p>
            </div>
          </div>

            <div className="flex items-center gap-2 bg-slate-50 p-2 border border-slate-300">
              <Filter className="w-4 h-4 text-[#002b49]" />
              <label htmlFor="jurisdiction-select" className="text-xs font-bold text-slate-700">
                {language === 'en' ? 'Jurisdiction Filter:' : 'अधिकार क्षेत्र:'}
              </label>
              <select
                id="jurisdiction-select"
                value={selectedJurisdiction}
                onChange={(e) => setSelectedJurisdiction(e.target.value)}
                className="bg-white text-slate-800 text-xs font-bold p-1 border border-slate-300 focus:outline-none"
              >
                <option value="ALL">{language === 'en' ? '-- All Assigned Tehsils --' : '-- सभी अधिकार क्षेत्र --'}</option>
                {currentUser.jurisdiction.map((j) => (
                  <option key={j} value={j}>{j}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

      {/* Hon'ble Prime Minister's Directive on Good Governance */}
      <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#002b49] text-white p-3.5 border-l-4 border-l-[#f37021] flex items-center justify-between gap-4 flex-wrap shadow-xs">
        <div className="flex items-center gap-3.5">
          <img 
            src="/assets/pm_modi_thumb.jpg" 
            alt="Shri Narendra Modi, Prime Minister of India" 
            className="w-12 h-12 rounded-full object-cover object-top border-2 border-[#f37021] shadow-xs flex-shrink-0"
          />
          <div className="text-left">
            <p className="text-xs italic text-amber-200 font-serif leading-snug">
              {language === 'en'
                ? '"Citizen trust is paramount in land acquisition. Every objection must receive a fair hearing, every compensation award must be statutory, and every payment must reach the farmer directly."'
                : '“भूमि अधिग्रहण में नागरिक विश्वास सर्वोपरि है। हर आपत्ति की निष्पक्ष सुनवाई, वैधानिक मुआवजा और किसानों तक सीधी राशि पहुंचना हमारी प्रतिबद्धता है।”'}
            </p>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[11px] font-bold text-white">
                {language === 'en' ? 'Shri Narendra Modi' : 'श्री नरेन्द्र मोदी'}
              </span>
              <span className="text-[10px] text-amber-300">
                • {language === 'en' ? "Hon'ble Prime Minister of India" : 'माननीय प्रधानमंत्री, भारत'}
              </span>
            </div>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-2 bg-white/10 px-2.5 py-1 rounded-xs border border-white/20 text-[10px] font-semibold text-slate-200">
          <span className="w-1.5 h-1.5 rounded-full bg-[#138808] animate-pulse"></span>
          <span>{language === 'en' ? 'Digital India Land Governance' : 'डिजिटल इंडिया भू-प्रशासन'}</span>
        </div>
      </div>

      {/* GIGW 3.0 Accessible Horizontally Scrolling Government Schemes Banner */}
      <GigwSchemeScrollBanner 
        language={language}
        title="Government Flagship Welfare Schemes & Statutory Directives"
        titleHi="प्रमुख केंद्रीय जन-कल्याणकारी योजनाएं एवं सांविधिक निर्देश"
      />

      {/* Primary KPI Grid (Rectangular Government Style Boxes) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* Box 1 */}
        <div className="bg-white border border-slate-300 p-3.5 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Active Acquisition Cases' : 'सक्रिय अधिग्रहण प्रकरण'}
              </p>
              <h3 className="text-2xl font-black text-[#0b3866] mt-0.5">
                {totalCases}
              </h3>
            </div>
            <div className="p-2 bg-[#e8f1f8] text-[#0b3866]">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-200 flex justify-between text-[11px]">
            <span className="font-bold text-red-700">
              {criticalCases} {language === 'en' ? 'Critical Risk' : 'अति संवेदनशील'}
            </span>
            <span className="text-slate-500">
              {highRiskCases} High &bull; {lowRiskCases} Low
            </span>
          </div>
        </div>

        {/* Box 2 */}
        <div className="bg-white border border-slate-300 p-3.5 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Statutory Milestones' : 'सांविधिक समय-सीमा'}
              </p>
              <h3 className="text-2xl font-black text-red-700 mt-0.5">
                {breachedDeadlines} <span className="text-xs font-semibold text-slate-600">Breached</span>
              </h3>
            </div>
            <div className="p-2 bg-red-50 text-red-700">
              <Clock className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-200 flex justify-between text-[11px]">
            <span className="text-[#f37021] font-bold">
              {approachingDeadlines} {language === 'en' ? 'Due in ≤15 days' : '15 दिनों में देय'}
            </span>
            <span className="text-slate-500">RFCTLARR Sec 19/23</span>
          </div>
        </div>

        {/* Box 3 */}
        <div className="bg-white border border-slate-300 p-3.5 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Blocking Issues & Objections' : 'अवरोधक त्रुटियां व आपत्तियां'}
              </p>
              <h3 className="text-2xl font-black text-red-700 mt-0.5">
                {totalOpenBlockingIssues} <span className="text-xs font-semibold text-slate-600">Blocking</span>
              </h3>
            </div>
            <div className="p-2 bg-amber-50 text-amber-800">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-200 flex justify-between text-[11px]">
            <span className="text-slate-800 font-semibold">
              {totalUndisposedObjections} {language === 'en' ? 'Sec 15 Objections' : 'लंबित आपत्तियां'}
            </span>
            <span className="text-amber-700 font-bold">{totalOpenMajorIssues} Major</span>
          </div>
        </div>

        {/* Box 4 */}
        <div className="bg-white border border-slate-300 p-3.5 flex flex-col justify-between">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                {language === 'en' ? 'Disbursed (PFMS DBT)' : 'संवितरित मुआवजा राशि'}
              </p>
              <h3 className="text-xl font-black text-[#138808] mt-0.5">
                {formatCurrencyINR(totalDisbursed)}
              </h3>
            </div>
            <div className="p-2 bg-emerald-50 text-[#138808]">
              <IndianRupee className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-200 flex justify-between text-[11px]">
            <span className="text-slate-600">
              {disbursementRate}% of {formatCurrencyINR(totalAwarded)}
            </span>
            <span className="font-bold text-[#138808]">Direct PFMS</span>
          </div>
        </div>
      </div>

      {/* Middle Grid: Statutory Stage Throughput & AI Delay Spectrum */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Stage Progress (2 cols) */}
        <div className="lg:col-span-2 bg-white border border-slate-300 p-4 space-y-3">
          <div className="border-b border-slate-200 pb-2 flex justify-between items-center">
            <h3 className="text-xs font-bold text-[#0b3866] uppercase tracking-wide flex items-center gap-1.5">
              <BarChart3 className="w-4 h-4 text-[#f37021]" />
              <span>{language === 'en' ? 'STATUTORY LIFECYCLE CASE DISTRIBUTION (RFCTLARR 2013)' : 'सांविधिक चरणवार प्रकरण वितरण'}</span>
            </h3>
            <span className="text-[10px] text-slate-500">Active Stages</span>
          </div>

          <div className="space-y-2 pt-1">
            {stagesList.map((item, idx) => {
              const count = filteredCases.filter(c => c.stage === item.stage).length;
              const percent = totalCases > 0 ? (count / totalCases) * 100 : 0;
              const hasCritical = filteredCases.some(c => c.stage === item.stage && c.riskBand === 'CRITICAL');

              return (
                <div key={item.stage} className="space-y-1 text-xs">
                  <div className="flex justify-between font-semibold text-slate-800">
                    <span className="flex items-center gap-1.5">
                      <span className="w-4 h-4 bg-[#0b3866] text-white flex items-center justify-center text-[10px] font-bold">
                        {idx + 1}
                      </span>
                      <span>{language === 'en' ? item.label : item.labelHi}</span>
                    </span>
                    <span className="font-mono text-slate-700">
                      {hasCritical && (
                        <span className="text-[10px] px-1 py-0.2 bg-red-100 text-red-800 font-bold border border-red-300 mr-2">
                          Delay Risk
                        </span>
                      )}
                      <strong>{count}</strong> ({percent.toFixed(0)}%)
                    </span>
                  </div>

                  <div className="h-2.5 w-full bg-slate-100 border border-slate-200 flex">
                    <div
                      className={`h-full ${hasCritical ? 'bg-red-600' : 'bg-[#0b3866]'}`}
                      style={{ width: `${Math.max(percent, count > 0 ? 10 : 0)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* AI Delay Risk Spectrum (1 col) */}
        <div className="bg-white border border-slate-300 p-4 space-y-3 flex flex-col justify-between">
          <div>
            <div className="border-b border-slate-200 pb-2">
              <h3 className="text-xs font-bold text-[#0b3866] uppercase tracking-wide flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-[#f37021]" />
                <span>{language === 'en' ? 'AI DELAY RISK SPECTRUM' : 'एआई विलंब जोखिम वर्गीकरण'}</span>
              </h3>
              <p className="text-[10px] text-slate-500 mt-0.5">Calibrated ML Early-Warning (90-day horizon)</p>
            </div>

            <div className="mt-3 space-y-1.5 text-xs">
              <div className="p-2 bg-red-50 border border-red-200 flex justify-between items-center">
                <div className="font-bold text-red-800">CRITICAL (p ≥ 0.75)</div>
                <span className="font-mono font-bold text-red-800">{criticalCases}</span>
              </div>
              <div className="p-2 bg-amber-50 border border-amber-200 flex justify-between items-center">
                <div className="font-bold text-amber-800">HIGH (0.50 ≤ p &lt; 0.75)</div>
                <span className="font-mono font-bold text-amber-800">{highRiskCases}</span>
              </div>
              <div className="p-2 bg-slate-50 border border-slate-200 flex justify-between items-center">
                <div className="font-bold text-slate-700">MEDIUM (0.25 ≤ p &lt; 0.50)</div>
                <span className="font-mono font-bold text-slate-700">{mediumRiskCases}</span>
              </div>
              <div className="p-2 bg-emerald-50 border border-emerald-200 flex justify-between items-center">
                <div className="font-bold text-emerald-800">LOW (p &lt; 0.25)</div>
                <span className="font-mono font-bold text-emerald-800">{lowRiskCases}</span>
              </div>
            </div>
          </div>

          <div className="pt-2 text-[10px] text-slate-500 border-t border-slate-200 flex justify-between items-center">
            <span>Model: Calibrated XGBoost v2.4</span>
            <span className="font-semibold text-emerald-700">ECE: 0.038</span>
          </div>
        </div>
      </div>

      {/* Priority Case Registry Table */}
      <div className="bg-white border border-slate-300">
        <div className="bg-[#0b3866] text-white px-3 py-1.5 font-bold text-xs flex justify-between items-center border-b border-[#0b3866]">
          <div className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5 text-[#f37021]" />
            <span>{language === 'en' ? 'PRIORITY LAND ACQUISITION CASE REGISTRY' : 'प्राथमिकता भू-अधिग्रहण प्रकरण पंजी'}</span>
          </div>
          <span className="text-[10px] text-slate-200">Click row to open 360° workspace</span>
        </div>

        <div className="overflow-x-auto">
          <table className="gov-table">
            <thead>
              <tr>
                <th>Case Reference</th>
                <th>Project Name</th>
                <th>Village / Tehsil</th>
                <th>Current Stage</th>
                <th>Statutory Deadline</th>
                <th>AI Risk</th>
                <th>Disbursed / Awarded</th>
                <th className="text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredCases.map((c) => {
                const isOverdue = c.isBreached || c.daysRemaining < 0;
                return (
                  <tr 
                    key={c.id}
                    onClick={() => {
                      setSelectedCaseId(c.id);
                      onNavigateToCase(c.id);
                    }}
                    className="cursor-pointer"
                  >
                    <td className="font-mono font-bold text-[#0b3866]">
                      {c.caseReference}
                    </td>
                    <td className="font-medium text-slate-900 max-w-[200px] truncate">
                      {language === 'en' ? c.projectName : c.projectNameHi}
                    </td>
                    <td className="text-slate-700">
                      {c.village}, {c.tehsil}
                    </td>
                    <td>
                      <span className="px-1.5 py-0.5 bg-[#e8f1f8] text-[#0b3866] border border-[#0b3866]/30 font-bold text-[10px]">
                        {c.stage.replace('STAGE_', '').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      <span className={`font-semibold ${isOverdue ? 'text-red-700' : 'text-slate-800'}`}>
                        {formatDate(c.stageDeadline)}
                      </span>
                      {isOverdue ? (
                        <span className="block text-[10px] text-red-700 font-bold">
                          {Math.abs(c.daysRemaining)}d Breached
                        </span>
                      ) : (
                        <span className="block text-[10px] text-slate-500">
                          ({c.daysRemaining}d left)
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`px-1.5 py-0.5 text-[10px] font-bold ${
                        c.riskBand === 'CRITICAL' ? 'bg-red-100 text-red-800 border border-red-300' :
                        c.riskBand === 'HIGH' ? 'bg-amber-100 text-amber-800 border border-amber-300' :
                        c.riskBand === 'MEDIUM' ? 'bg-slate-100 text-slate-800 border border-slate-300' :
                        'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      }`}>
                        {c.riskBand} ({Math.round(c.riskProbability * 100)}%)
                      </span>
                    </td>
                    <td className="font-mono">
                      <div className="font-bold text-[#138808]">{formatCurrencyINR(c.totalDisbursedAmount)}</div>
                      <div className="text-[10px] text-slate-500">{formatCurrencyINR(c.totalAwardedAmount)} Awarded</div>
                    </td>
                    <td className="text-right">
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCaseId(c.id);
                          onNavigateToCase(c.id);
                        }}
                        className="px-2.5 py-1 bg-[#0b3866] hover:bg-[#002b49] text-white font-bold text-[10px]"
                      >
                        {language === 'en' ? 'Open Case' : 'प्रकरण खोलें'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
