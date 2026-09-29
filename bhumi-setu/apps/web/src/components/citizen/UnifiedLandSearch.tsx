import React, { useState } from 'react';
import { 
  Search, 
  MapPin, 
  FileText, 
  Map, 
  User, 
  CheckCircle2, 
  AlertCircle, 
  Layers, 
  ChevronRight, 
  Sparkles,
  ExternalLink,
  ShieldCheck,
  RefreshCw,
  Eye,
  FileCheck
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { SAMPLE_PROPERTY_DEMO, DemoProperty } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

type SearchMode = 'LOCATION' | 'ULPIN' | 'SURVEY' | 'OWNER' | 'MAP';

export const UnifiedLandSearch: React.FC<{
  onSelectProperty: (property: DemoProperty) => void;
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onSelectProperty, onNavigateTab }) => {
  const { language, addToast } = useApp();

  const [searchMode, setSearchMode] = useState<SearchMode>('LOCATION');

  // Hierarchical Dropdowns
  const [selectedState, setSelectedState] = useState('Maharashtra');
  const [selectedDistrict, setSelectedDistrict] = useState('Nagpur');
  const [selectedTehsil, setSelectedTehsil] = useState('Nagpur (Rural)');
  const [selectedVillage, setSelectedVillage] = useState('Demo Village (Besa)');
  const [surveyInput, setSurveyInput] = useState('123/4');
  const [ulpinInput, setUlpinInput] = useState('27712049001234');
  const [ownerInput, setOwnerInput] = useState('');

  // Results State
  const [hasSearched, setHasSearched] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [resultProperty, setResultProperty] = useState<DemoProperty | null>(SAMPLE_PROPERTY_DEMO);

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      setHasSearched(true);
      setResultProperty(SAMPLE_PROPERTY_DEMO);
      addToast({
        type: 'success',
        message: 'Demonstration land record found: MH-NGP-00012345',
        messageHi: 'नमूना भू-अभिलेख प्राप्त: MH-NGP-00012345'
      });
    }, 400);
  };

  const handleLoadDemo = () => {
    setSelectedState('Maharashtra');
    setSelectedDistrict('Nagpur');
    setSelectedTehsil('Nagpur (Rural)');
    setSelectedVillage('Demo Village (Besa)');
    setSurveyInput('123/4');
    setUlpinInput('27712049001234');
    setResultProperty(SAMPLE_PROPERTY_DEMO);
    setHasSearched(true);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner / Disclaimer */}
      <div className="bg-[#002642] text-white p-4 rounded-xs border-b-2 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold">
              {language === 'en' ? 'Search Land Records' : 'भू-अभिलेख खोजें'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#f37021] text-white tracking-wider">
              SAMPLE DATA
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-0.5">
            {language === 'en'
              ? 'Multi-mode query engine across State RoR, Cadastral Maps, and Bhu-Aadhaar ULPIN.'
              : 'राज्य अधिकार अभिलेख, भू-नक्शा एवं १४-अंकीय भू-आधार के लिए एकीकृत खोज प्रणाली।'}
          </p>
        </div>

        <button
          onClick={handleLoadDemo}
          className="px-3.5 py-1.5 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs border border-white/25 flex items-center gap-1.5 transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5 text-amber-300" />
          <span>{language === 'en' ? 'Load Sample Property (MH-NGP)' : 'नमूना रिकॉर्ड लोड करें'}</span>
        </button>
      </div>

      {/* Search Mode Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setSearchMode('LOCATION')}
          className={`px-3.5 py-2 text-xs font-bold rounded-xs flex items-center gap-1.5 transition-colors ${
            searchMode === 'LOCATION'
              ? 'bg-[#002642] text-white shadow-xs'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <MapPin className="w-3.5 h-3.5" />
          <span>{language === 'en' ? 'Search by Hierarchy (State → Village)' : 'स्थान आधारित खोज'}</span>
        </button>

        <button
          onClick={() => setSearchMode('ULPIN')}
          className={`px-3.5 py-2 text-xs font-bold rounded-xs flex items-center gap-1.5 transition-colors ${
            searchMode === 'ULPIN'
              ? 'bg-[#002642] text-white shadow-xs'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <Sparkles className="w-3.5 h-3.5 text-[#f37021]" />
          <span>{language === 'en' ? 'Search by ULPIN / Bhu-Aadhaar' : 'भू-आधार (ULPIN) द्वारा'}</span>
        </button>

        <button
          onClick={() => setSearchMode('SURVEY')}
          className={`px-3.5 py-2 text-xs font-bold rounded-xs flex items-center gap-1.5 transition-colors ${
            searchMode === 'SURVEY'
              ? 'bg-[#002642] text-white shadow-xs'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>{language === 'en' ? 'Search by Survey / Khasra No.' : 'सर्वे / खसरा क्रमांक द्वारा'}</span>
        </button>

        <button
          onClick={() => setSearchMode('OWNER')}
          className={`px-3.5 py-2 text-xs font-bold rounded-xs flex items-center gap-1.5 transition-colors ${
            searchMode === 'OWNER'
              ? 'bg-[#002642] text-white shadow-xs'
              : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
          }`}
        >
          <User className="w-3.5 h-3.5" />
          <span>{language === 'en' ? 'Search by Owner Name' : 'भूस्वामी नाम द्वारा'}</span>
        </button>

        <button
          onClick={() => onNavigateTab('GIS_MAP')}
          className="px-3.5 py-2 text-xs font-bold rounded-xs bg-[#138808] hover:bg-[#0f6c06] text-white flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <Map className="w-3.5 h-3.5" />
          <span>{language === 'en' ? 'Search on Interactive Map' : 'मानचित्र पर खोजें'}</span>
        </button>
      </div>

      {/* Main Professional Search Card */}
      <div className="bg-white border border-slate-300 rounded-xs shadow-sm p-5 text-xs text-left">
        <form onSubmit={handleSearch} className="space-y-4">
          {searchMode === 'LOCATION' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  {language === 'en' ? 'State' : 'राज्य'} <span className="text-red-500">*</span>
                </label>
                <select
                  value={selectedState}
                  onChange={(e) => setSelectedState(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-xs bg-white font-medium text-slate-800"
                >
                  <option value="Maharashtra">Maharashtra (महाराष्ट्र)</option>
                  <option value="Uttar Pradesh">Uttar Pradesh (उत्तर प्रदेश)</option>
                  <option value="Karnataka">Karnataka (कर्नाटक)</option>
                  <option value="Madhya Pradesh">Madhya Pradesh (मध्य प्रदेश)</option>
                  <option value="Gujarat">Gujarat (गुजरात)</option>
                  <option value="Rajasthan">Rajasthan (राजस्थान)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  {language === 'en' ? 'District' : 'जिला'} <span className="text-red-500">*</span>
                </label>
                <select
                  value={selectedDistrict}
                  onChange={(e) => setSelectedDistrict(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-xs bg-white font-medium text-slate-800"
                >
                  <option value="Nagpur">Nagpur (नागपुर)</option>
                  <option value="Pune">Pune (पुणे)</option>
                  <option value="Nashik">Nashik (नाशिक)</option>
                  <option value="Thane">Thane (ठाणे)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  {language === 'en' ? 'Tehsil / Taluka' : 'तहसील / तालुका'} <span className="text-red-500">*</span>
                </label>
                <select
                  value={selectedTehsil}
                  onChange={(e) => setSelectedTehsil(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-xs bg-white font-medium text-slate-800"
                >
                  <option value="Nagpur (Rural)">Nagpur (Rural) (नागपुर ग्रामीण)</option>
                  <option value="Nagpur (Urban)">Nagpur (Urban) (नागपुर शहर)</option>
                  <option value="Kamptee">Kamptee (कामठी)</option>
                  <option value="Hingna">Hingna (हिंगणा)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  {language === 'en' ? 'Village' : 'ग्राम'} <span className="text-red-500">*</span>
                </label>
                <select
                  value={selectedVillage}
                  onChange={(e) => setSelectedVillage(e.target.value)}
                  className="w-full p-2 border border-slate-300 rounded-xs bg-white font-medium text-slate-800"
                >
                  <option value="Demo Village (Besa)">Demo Village (Besa / बेसा)</option>
                  <option value="Pipla">Pipla (पिंपळा)</option>
                  <option value="Wadi">Wadi (वाडी)</option>
                  <option value="Ghogli">Ghogli (घोगली)</option>
                </select>
              </div>

              <div className="sm:col-span-2">
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  {language === 'en' ? 'Survey Number / Khasra / Gat No.' : 'सर्वे / खसरा / गट क्रमांक'}
                </label>
                <input
                  type="text"
                  value={surveyInput}
                  onChange={(e) => setSurveyInput(e.target.value)}
                  placeholder="e.g. 123/4"
                  className="w-full p-2 border border-slate-300 rounded-xs font-mono"
                />
              </div>

              <div className="sm:col-span-2">
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  {language === 'en' ? 'ULPIN (14-Digit Bhu-Aadhaar Optional)' : '१४-अंकीय भू-आधार (वैकल्पिक)'}
                </label>
                <input
                  type="text"
                  value={ulpinInput}
                  onChange={(e) => setUlpinInput(e.target.value)}
                  placeholder="e.g. 27712049001234"
                  className="w-full p-2 border border-slate-300 rounded-xs font-mono"
                />
              </div>
            </div>
          )}

          {searchMode === 'ULPIN' && (
            <div className="max-w-xl space-y-2">
              <label className="block text-[11px] font-bold text-slate-700 uppercase">
                {language === 'en' ? 'Enter 14-Digit Bhu-Aadhaar (ULPIN)' : '१४-अंकीय भू-आधार दर्ज करें'} <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={ulpinInput}
                onChange={(e) => setUlpinInput(e.target.value)}
                placeholder="27XXXXXXXXXXXXXX"
                className="w-full p-2.5 border border-slate-300 rounded-xs font-mono text-sm tracking-wider"
              />
              <p className="text-[10px] text-slate-500">
                Standard: 2-digit State + 3-digit District + 3-digit Sub-district + 6-digit Parcel/Subdivision.
              </p>
            </div>
          )}

          {searchMode === 'SURVEY' && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">State</label>
                <select value={selectedState} onChange={(e) => setSelectedState(e.target.value)} className="w-full p-2 border border-slate-300 rounded-xs">
                  <option value="Maharashtra">Maharashtra</option>
                  <option value="Uttar Pradesh">Uttar Pradesh</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">District</label>
                <input type="text" value={selectedDistrict} onChange={(e) => setSelectedDistrict(e.target.value)} className="w-full p-2 border border-slate-300 rounded-xs" />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">Survey / Khasra No.</label>
                <input type="text" value={surveyInput} onChange={(e) => setSurveyInput(e.target.value)} className="w-full p-2 border border-slate-300 rounded-xs font-mono" />
              </div>
            </div>
          )}

          {searchMode === 'OWNER' && (
            <div className="max-w-xl space-y-2">
              <label className="block text-[11px] font-bold text-slate-700 uppercase">
                {language === 'en' ? 'Recorded Owner Name (Masked Search)' : 'भूस्वामी का नाम'}
              </label>
              <input
                type="text"
                value={ownerInput}
                onChange={(e) => setOwnerInput(e.target.value)}
                placeholder="e.g. Rameshwar Sharma"
                className="w-full p-2 border border-slate-300 rounded-xs"
              />
              <p className="text-[10px] text-amber-700 bg-amber-50 p-2 rounded-xs border border-amber-200">
                DPDP Act 2023 Compliance: Real citizen personal data is never displayed publicly. Fictional sample records are returned for demonstration.
              </p>
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="px-6 py-2.5 bg-[#002642] hover:bg-[#0b3866] text-white font-extrabold rounded-xs flex items-center gap-2 shadow-xs transition-colors"
            >
              {isLoading ? (
                <RefreshCw className="w-4 h-4 animate-spin text-amber-300" />
              ) : (
                <Search className="w-4 h-4 text-[#f37021]" />
              )}
              <span>{language === 'en' ? 'Search Land Records' : 'अभिलेख खोजें'}</span>
            </button>

            <button
              type="button"
              onClick={handleLoadDemo}
              className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xs transition-colors"
            >
              {language === 'en' ? 'Reset to Demo' : 'रीसेट'}
            </button>
          </div>
        </form>
      </div>

      {/* Result Demonstration Card */}
      {hasSearched && resultProperty && (
        <div className="bg-white border-2 border-[#0b3866] rounded-xs shadow-md overflow-hidden text-left animate-fadeIn">
          {/* Header Strip with Official Badges */}
          <div className="bg-gradient-to-r from-[#002642] via-[#0b3866] to-[#002b49] text-white p-4 flex flex-wrap justify-between items-center gap-3 border-b-2 border-[#f37021]">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-sm sm:text-base tracking-wide">
                  Property ID: {resultProperty.id}
                </span>
                <span className="px-2 py-0.5 bg-[#f37021] text-white text-[9px] font-black rounded-xs uppercase">
                  SAMPLE DATA
                </span>
                <span className="px-2 py-0.5 bg-[#138808] text-white text-[9px] font-bold rounded-xs">
                  {resultProperty.recordStatus}
                </span>
              </div>
              <p className="text-[11px] text-slate-300">
                ULPIN (Bhu-Aadhaar): <strong className="font-mono text-amber-300">{resultProperty.ulpin}</strong>
              </p>
            </div>

            <div className="text-right text-[11px] text-slate-300">
              <div>Source: <span className="text-white font-semibold">{resultProperty.sourcePortal}</span></div>
              <div className="text-[10px] text-slate-400">Last Updated: {resultProperty.lastUpdated}</div>
            </div>
          </div>

          {/* Key Specifications Grid as specified in Section 4 */}
          <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 bg-slate-50/60 border-b border-slate-200 text-xs">
            <div className="bg-white p-3 rounded-xs border border-slate-200 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-500">Location</div>
              <div className="font-bold text-sm text-[#002642] mt-0.5">
                {resultProperty.village}
              </div>
              <div className="text-[11px] text-slate-600 mt-0.5">
                Tehsil: {resultProperty.tehsil} • District: {resultProperty.district}
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5 font-medium">
                State: {resultProperty.state}
              </div>
            </div>

            <div className="bg-white p-3 rounded-xs border border-slate-200 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-500">Survey &amp; Cadastre</div>
              <div className="font-bold text-sm text-[#002642] mt-0.5 font-mono">
                Survey No: {resultProperty.surveyNumber}
              </div>
              <div className="text-[11px] text-slate-600 mt-0.5 font-mono">
                Sheet: {resultProperty.cadastralSheetNo}
              </div>
              <div className="text-[10px] text-emerald-700 font-semibold mt-0.5">
                Subdivision: {resultProperty.subdivision}
              </div>
            </div>

            <div className="bg-white p-3 rounded-xs border border-slate-200 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-500">Area &amp; Classification</div>
              <div className="font-bold text-sm text-[#002642] mt-0.5">
                {resultProperty.areaHectares} Hectares
              </div>
              <div className="text-[11px] text-slate-600 mt-0.5">
                Approx. {resultProperty.areaAcres} Acres ({resultProperty.areaSqMeters.toLocaleString()} m²)
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {resultProperty.landType}
              </div>
            </div>

            <div className="bg-white p-3 rounded-xs border border-slate-200 shadow-2xs">
              <div className="text-[10px] uppercase font-bold text-slate-500">Active Workflow</div>
              <div className="font-bold text-xs text-amber-700 mt-0.5">
                {resultProperty.activeMutation.currentStage}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                Application: <span className="font-mono font-bold text-slate-700">{resultProperty.activeMutation.applicationId}</span>
              </div>
              <div className="text-[10px] text-[#138808] font-bold mt-0.5">
                Encumbrance: {resultProperty.encumbranceStatus}
              </div>
            </div>
          </div>

          {/* Action Triggers to Seamlessly Navigate to Other Modules */}
          <div className="p-4 bg-white flex flex-wrap items-center justify-between gap-3">
            <div className="text-[11px] text-slate-600 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-[#138808]" />
              <span>
                Preliminary data compiled from 4 statutory registries for academic review.
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => {
                  onSelectProperty(resultProperty);
                  onNavigateTab('PROPERTY_INTEL');
                }}
                className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
              >
                <span>Open Property Intelligence Dashboard</span>
                <ChevronRight className="w-3.5 h-3.5 text-[#f37021]" />
              </button>

              <button
                onClick={() => onNavigateTab('GIS_MAP')}
                className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xs border border-slate-300 flex items-center gap-1.5 transition-colors"
              >
                <Map className="w-3.5 h-3.5 text-[#002642]" />
                <span>View on Cadastral Map</span>
              </button>

              <button
                onClick={() => onNavigateTab('REPORTS')}
                className="px-3.5 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
              >
                <FileCheck className="w-3.5 h-3.5" />
                <span>Generate Preliminary Report</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
