import React, { useState } from 'react';
import { 
  Map, 
  Layers, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Compass, 
  MapPin, 
  Info, 
  ShieldCheck, 
  Sparkles,
  ExternalLink,
  ChevronRight,
  Eye,
  CheckCircle2
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { SAMPLE_PROPERTY_DEMO, DemoProperty } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

interface SimulatedParcel {
  id: string;
  surveyNumber: string;
  ulpin: string;
  areaHa: number;
  recordStatus: string;
  ownerMasked: string;
  isMainProperty?: boolean;
  coordinates: { x: number; y: number; w: number; h: number };
}

const PARCEL_NETWORK: SimulatedParcel[] = [
  {
    id: 'P-123-4',
    surveyNumber: '123/4',
    ulpin: '27712049001234',
    areaHa: 2.50,
    recordStatus: 'Digitized & Verified',
    ownerMasked: 'Rameshwar K. Sharma & 2 Co-sharers',
    isMainProperty: true,
    coordinates: { x: 340, y: 190, w: 220, h: 160 }
  },
  {
    id: 'P-123-3',
    surveyNumber: '123/3',
    ulpin: '27712049001233',
    areaHa: 1.80,
    recordStatus: 'Digitized',
    ownerMasked: 'S. N. Deshmukh (Demo)',
    coordinates: { x: 120, y: 190, w: 210, h: 160 }
  },
  {
    id: 'P-123-5',
    surveyNumber: '123/5',
    ulpin: '27712049001235',
    areaHa: 2.10,
    recordStatus: 'Digitized',
    ownerMasked: 'Bapu Rao Patil (Demo)',
    coordinates: { x: 570, y: 190, w: 200, h: 160 }
  },
  {
    id: 'P-122-1',
    surveyNumber: '122/1',
    ulpin: '27712049001221',
    areaHa: 3.40,
    recordStatus: 'Digitized',
    ownerMasked: 'Gram Panchayat Common Land',
    coordinates: { x: 340, y: 20, w: 220, h: 160 }
  },
  {
    id: 'P-124-2',
    surveyNumber: '124/2',
    ulpin: '27712049001242',
    areaHa: 1.95,
    recordStatus: 'Mutation Pending',
    ownerMasked: 'Anand V. Joshi (Demo)',
    coordinates: { x: 340, y: 360, w: 220, h: 150 }
  }
];

export const PropertyMapIntelligence: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language } = useApp();
  const [mapLayer, setMapLayer] = useState<'CADASTRAL' | 'SATELLITE' | 'ROAD'>('CADASTRAL');
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [selectedParcel, setSelectedParcel] = useState<SimulatedParcel>(PARCEL_NETWORK[0]);

  const handleZoomIn = () => setZoomLevel(prev => Math.min(prev + 15, 160));
  const handleZoomOut = () => setZoomLevel(prev => Math.max(prev - 15, 70));
  const handleResetZoom = () => setZoomLevel(100);

  return (
    <div className="space-y-6 text-left">
      {/* 1. Header Banner */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'Property Map Intelligence & GIS Cadastre' : 'भू-मानचित्र आसूचना एवं डिजिटल कैडस्ट्रल नक्शा'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#138808] text-white">
              DEMONSTRATION GIS DATA
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Interactive cadastral GIS viewer inspecting parcel boundaries, adjoining surveys, water canals, village roads, and ULPIN centroids.'
              : 'सीमाओं, निकटवर्ती सर्वे नंबरों, पहुंच मार्ग, नहरों एवं यूएलपीआईएन केंद्रबिंदु की परस्पर संवादात्मक जीआईएस जांच।'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigateTab('PROPERTY_INTEL')}
            className="px-3.5 py-1.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
          >
            <span>Property Intelligence View</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 2. Interactive Controls & Layer Switcher Bar */}
      <div className="bg-white p-3 rounded-xs border border-slate-300 shadow-2xs flex flex-wrap justify-between items-center gap-3 text-xs">
        {/* Layer Selector */}
        <div className="flex items-center gap-2">
          <span className="font-bold text-slate-700 flex items-center gap-1">
            <Layers className="w-3.5 h-3.5 text-[#002642]" />
            <span>Map Layer:</span>
          </span>

          <button
            onClick={() => setMapLayer('CADASTRAL')}
            className={`px-3 py-1.5 rounded-xs font-bold transition-colors ${
              mapLayer === 'CADASTRAL'
                ? 'bg-[#002642] text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            Cadastral (BhuNaksha)
          </button>

          <button
            onClick={() => setMapLayer('SATELLITE')}
            className={`px-3 py-1.5 rounded-xs font-bold transition-colors ${
              mapLayer === 'SATELLITE'
                ? 'bg-[#002642] text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            Satellite Imagery
          </button>

          <button
            onClick={() => setMapLayer('ROAD')}
            className={`px-3 py-1.5 rounded-xs font-bold transition-colors ${
              mapLayer === 'ROAD'
                ? 'bg-[#002642] text-white shadow-xs'
                : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
            }`}
          >
            Road &amp; Infrastructure
          </button>
        </div>

        {/* Zoom Controls */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-500 font-mono">Zoom: {zoomLevel}%</span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-xs text-slate-700 font-bold"
            title="Zoom In (+)"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-xs text-slate-700 font-bold"
            title="Zoom Out (-)"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetZoom}
            className="px-2 py-1 text-[11px] bg-slate-100 hover:bg-slate-200 rounded-xs text-slate-700 font-semibold"
          >
            Reset
          </button>
        </div>
      </div>

      {/* 3. Main Interactive Map Canvas & Parcel Inspector Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: SVG Cadastral Canvas */}
        <div className="lg:col-span-8 bg-slate-900 rounded-xs border-2 border-slate-400 overflow-hidden relative shadow-md">
          {/* Layer Notice Badge */}
          <div className="absolute top-3 left-3 z-10 bg-black/75 backdrop-blur-xs text-white px-3 py-1 rounded-xs text-[10px] font-mono border border-white/20 flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#138808] animate-pulse"></span>
            <span>Layer: {mapLayer} • EPSG: 4326 WGS-84 (Simulated)</span>
          </div>

          <div className="absolute top-3 right-3 z-10 bg-amber-500 text-black px-2.5 py-1 rounded-xs text-[10px] font-black uppercase">
            DEMONSTRATION GIS DATA
          </div>

          {/* SVG Map Container */}
          <div className="w-full h-[460px] flex items-center justify-center overflow-auto p-4 select-none">
            <div 
              style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'center' }}
              className="transition-transform duration-200"
            >
              <svg width="860" height="530" viewBox="0 0 860 530" className="bg-[#112233] rounded-xs shadow-inner">
                {/* Background Grid Pattern */}
                <defs>
                  <pattern id="gisGrid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#223344" strokeWidth="0.8" />
                  </pattern>
                </defs>
                <rect width="860" height="530" fill="url(#gisGrid)" />

                {/* Village Boundary Outer Buffer (Green dashed line) */}
                <rect x="50" y="10" width="760" height="510" fill="none" stroke="#138808" strokeWidth="2.5" strokeDasharray="6,4" />
                <text x="65" y="32" fill="#22c55e" fontSize="11" fontWeight="bold">
                  Village Boundary: Demo Village (Besa Saja LGD 534921)
                </text>

                {/* Simulated Water Body / Northern Canal (Blue Ribbon) */}
                <path d="M 50 15 Q 400 35 810 15" stroke="#0ea5e9" strokeWidth="12" fill="none" opacity="0.75" />
                <text x="660" y="38" fill="#38bdf8" fontSize="10" fontWeight="bold">
                  Perennial Irrigation Canal (Minor-IV)
                </text>

                {/* Public Road / Cart Track (South Roadway) */}
                <path d="M 50 515 L 810 515" stroke="#f59e0b" strokeWidth="14" fill="none" opacity="0.8" />
                <text x="65" y="508" fill="#fef08a" fontSize="10" fontWeight="bold">
                  Public Cart Track / Approach Road (MDR-14 Link)
                </text>

                {/* Survey Parcels Polygons */}
                {PARCEL_NETWORK.map((parcel) => {
                  const isSelected = selectedParcel.id === parcel.id;
                  const isTarget = parcel.isMainProperty;

                  return (
                    <g
                      key={parcel.id}
                      onClick={() => setSelectedParcel(parcel)}
                      className="cursor-pointer transition-all"
                    >
                      <rect
                        x={parcel.coordinates.x}
                        y={parcel.coordinates.y}
                        width={parcel.coordinates.w}
                        height={parcel.coordinates.h}
                        fill={
                          isTarget
                            ? isSelected ? '#f37021' : '#c2410c'
                            : isSelected ? '#0b3866' : '#1e293b'
                        }
                        fillOpacity={isSelected ? 0.85 : 0.65}
                        stroke={isSelected ? '#ffffff' : isTarget ? '#f37021' : '#64748b'}
                        strokeWidth={isSelected ? 3 : 1.5}
                        rx="4"
                      />

                      {/* Survey Number Label */}
                      <text
                        x={parcel.coordinates.x + parcel.coordinates.w / 2}
                        y={parcel.coordinates.y + parcel.coordinates.h / 2 - 12}
                        textAnchor="middle"
                        fill="#ffffff"
                        fontSize="14"
                        fontWeight="bold"
                        fontFamily="monospace"
                      >
                        Survey {parcel.surveyNumber}
                      </text>

                      {/* Area Label */}
                      <text
                        x={parcel.coordinates.x + parcel.coordinates.w / 2}
                        y={parcel.coordinates.y + parcel.coordinates.h / 2 + 10}
                        textAnchor="middle"
                        fill="#e2e8f0"
                        fontSize="11"
                        fontWeight="semibold"
                      >
                        {parcel.areaHa} Ha
                      </text>

                      {/* ULPIN Centroid Marker */}
                      <circle
                        cx={parcel.coordinates.x + parcel.coordinates.w / 2}
                        cy={parcel.coordinates.y + parcel.coordinates.h / 2 + 28}
                        r="5"
                        fill={isTarget ? '#fde047' : '#38bdf8'}
                        stroke="#000000"
                        strokeWidth="1.5"
                      />

                      {isTarget && (
                        <text
                          x={parcel.coordinates.x + parcel.coordinates.w / 2}
                          y={parcel.coordinates.y + 22}
                          textAnchor="middle"
                          fill="#fef08a"
                          fontSize="10"
                          fontWeight="bold"
                        >
                          ★ Target Parcel
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          </div>

          {/* Map Footer Bar */}
          <div className="bg-slate-950 p-2.5 px-4 text-[10px] text-slate-400 flex flex-wrap justify-between items-center">
            <span>Coordinates Centroid: 21.0764° N, 79.0832° E</span>
            <span>Survey of India CORS Network Station: NGP-04</span>
          </div>
        </div>

        {/* Right: Selected Parcel Inspector Card */}
        <div className="lg:col-span-4 bg-white border border-slate-300 rounded-xs p-5 shadow-xs text-xs space-y-4">
          <div className="border-b border-slate-200 pb-3">
            <span className="text-[10px] uppercase font-bold text-slate-400">Inspected Cadastral Parcel</span>
            <div className="flex items-center justify-between mt-1">
              <h3 className="font-black text-lg text-[#002642]">
                Survey No: {selectedParcel.surveyNumber}
              </h3>
              <span className={`px-2 py-0.5 rounded-xs text-[10px] font-bold ${
                selectedParcel.isMainProperty 
                  ? 'bg-[#f37021] text-white' 
                  : 'bg-slate-100 text-slate-700'
              }`}>
                {selectedParcel.isMainProperty ? 'TARGET PARCEL' : 'ADJACENT HOLDING'}
              </span>
            </div>
          </div>

          <div className="space-y-2.5">
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">ULPIN (14-Digit Bhu-Aadhaar)</span>
              <div className="font-mono font-bold text-xs text-[#002642] mt-0.5">
                {selectedParcel.ulpin}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Area (GIS)</span>
                <div className="font-bold text-sm text-[#002642] mt-0.5">
                  {selectedParcel.areaHa} Hectares
                </div>
              </div>

              <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
                <span className="text-[10px] font-bold text-slate-400 uppercase">Status</span>
                <div className="font-bold text-xs text-emerald-700 mt-0.5">
                  {selectedParcel.recordStatus}
                </div>
              </div>
            </div>

            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Recorded Owner (DPDP Masked)</span>
              <div className="font-bold text-xs text-slate-800 mt-0.5">
                {selectedParcel.ownerMasked}
              </div>
            </div>
          </div>

          {/* Quick Action Navigation */}
          <div className="pt-2 space-y-2">
            <button
              onClick={() => onNavigateTab('PROPERTY_INTEL')}
              className="w-full py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>View Full Intelligence Record</span>
              <ChevronRight className="w-3.5 h-3.5 text-[#f37021]" />
            </button>

            <button
              onClick={() => onNavigateTab('RISK_ANALYSIS')}
              className="w-full py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xs border border-slate-300 flex items-center justify-center gap-1.5 transition-colors"
            >
              <span>Check Boundary Variance (0.05 Ha)</span>
            </button>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-200 rounded-xs text-[10px] text-[#002642]">
            <strong>GIS Cadastral Synchronization:</strong> Parcel boundary vector matches the Survey of India 2025 drone survey tiles.
          </div>
        </div>
      </div>
    </div>
  );
};
