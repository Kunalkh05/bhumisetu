import React from 'react';
import { 
  Printer, 
  Download, 
  Share2, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  FileText, 
  Building2, 
  MapPin, 
  Clock, 
  Landmark, 
  User, 
  ExternalLink,
  ChevronLeft
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { 
  SAMPLE_PROPERTY_DEMO, 
  PRELIMINARY_RISK_CHECKS, 
  PROPERTY_TIMELINE_SAMPLE, 
  MUTATION_TRACKING_SAMPLE,
  SAMPLE_EXTRACTED_DOCUMENTS 
} from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

export const ReportGeneratorView: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language, addToast } = useApp();
  const property = SAMPLE_PROPERTY_DEMO;

  const handlePrint = () => {
    window.print();
  };

  const handleDownload = () => {
    addToast({
      type: 'success',
      message: 'Downloading Preliminary Property Intelligence Report (PDF simulation)...',
      messageHi: 'प्रारंभिक सूचना रिपोर्ट डाउनलोड हो रही है...'
    });
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    addToast({
      type: 'info',
      message: 'Shareable report link copied to clipboard.',
      messageHi: 'रिपोर्ट लिंक कॉपी किया गया।'
    });
  };

  return (
    <div className="space-y-6 text-left max-w-5xl mx-auto">
      {/* 1. Print & Action Controls Bar (Hidden during window.print) */}
      <div className="bg-[#002642] text-white p-4 rounded-xs border-b-2 border-[#f37021] flex flex-wrap justify-between items-center gap-3 print:hidden">
        <button
          onClick={() => onNavigateTab('PROPERTY_INTEL')}
          className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handlePrint}
            className="px-4 py-2 bg-white text-[#002642] hover:bg-slate-100 font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Printer className="w-4 h-4 text-[#002642]" />
            <span>Print Report</span>
          </button>

          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-[#f37021] hover:bg-[#d95a10] text-white font-extrabold text-xs rounded-xs flex items-center gap-1.5 shadow-xs transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>Download Report (PDF)</span>
          </button>

          <button
            onClick={handleShare}
            className="px-3.5 py-2 bg-white/15 hover:bg-white/25 text-white font-bold text-xs rounded-xs border border-white/30 flex items-center gap-1.5 transition-colors"
          >
            <Share2 className="w-3.5 h-3.5" />
            <span>Share Report</span>
          </button>
        </div>
      </div>

      {/* 2. THE OFFICIAL PRELIMINARY REPORT DOCUMENT (PRINTABLE CONTAINER) */}
      <div className="bg-white border-2 border-slate-300 rounded-xs p-6 sm:p-10 shadow-lg text-slate-800 space-y-6 print:border-none print:shadow-none print:p-0">
        
        {/* MANDATORY PROMINENT DISCLAIMER HEADER AS REQUIRED IN SECTION 13 */}
        <div className="border-b-2 border-slate-900 pb-4 text-center space-y-1.5">
          <div className="text-[11px] font-black tracking-widest text-[#002642] uppercase">
            BHUMISETU • UNIFIED AI LAND INTELLIGENCE LAYER
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-[#002642] tracking-tight uppercase">
            PRELIMINARY INFORMATION REPORT
          </h1>
          <div className="bg-amber-100 border border-amber-300 p-2.5 rounded-xs text-[11px] text-amber-950 font-bold max-w-3xl mx-auto">
            “This report is generated for informational and preliminary verification purposes only. It is not a legal title certificate or government-issued clearance.”
          </div>
          <div className="text-[10px] text-slate-500 pt-1">
            Report Reference: <span className="font-mono font-bold text-slate-700">RPT-BHUMI-2026-0929-12345</span> • Timestamp: <strong>29 September 2026 • 14:30 IST</strong>
          </div>
        </div>

        {/* Section 1: Property Overview & Land Identification */}
        <div className="space-y-3">
          <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-[#002642] font-extrabold text-xs text-[#002642] uppercase">
            1. Property Overview &amp; Land Identification
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Property ID</span>
              <div className="font-mono font-bold text-[#002642] mt-0.5">{property.id}</div>
            </div>
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">ULPIN (Bhu-Aadhaar)</span>
              <div className="font-mono font-bold text-[#002642] mt-0.5">{property.ulpin}</div>
            </div>
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Survey / Gat No.</span>
              <div className="font-mono font-bold text-[#002642] mt-0.5">{property.surveyNumber}</div>
            </div>
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Total Area</span>
              <div className="font-bold text-[#002642] mt-0.5">{property.areaHectares} Ha ({property.areaAcres} Acres)</div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">State &amp; District</span>
              <div className="font-semibold text-slate-800 mt-0.5">{property.state}, {property.district}</div>
            </div>
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Tehsil &amp; Village</span>
              <div className="font-semibold text-slate-800 mt-0.5">{property.tehsil}, {property.village}</div>
            </div>
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Land Classification</span>
              <div className="font-semibold text-slate-800 mt-0.5">{property.landType}</div>
            </div>
            <div className="p-2 border border-slate-200 rounded-xs">
              <span className="text-[10px] font-bold text-slate-400 uppercase">Record Status</span>
              <div className="font-bold text-emerald-700 mt-0.5">{property.recordStatus}</div>
            </div>
          </div>
        </div>

        {/* Section 2: Ownership Information */}
        <div className="space-y-3">
          <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-[#002642] font-extrabold text-xs text-[#002642] uppercase flex justify-between items-center">
            <span>2. Ownership Information (Fictional / Sample Record)</span>
            <span className="text-[10px] font-bold text-amber-700">DPDP PRIVACY MASKED</span>
          </div>

          <table className="w-full text-xs border border-slate-200">
            <thead className="bg-slate-50 text-[10px] font-bold text-slate-600 uppercase border-b border-slate-200">
              <tr>
                <th className="p-2 text-left">Recorded Owner</th>
                <th className="p-2 text-left">Holding Nature</th>
                <th className="p-2 text-left">Share Ratio</th>
                <th className="p-2 text-left">Mutation Entry</th>
                <th className="p-2 text-left">Entry Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {property.owners.map((owner, idx) => (
                <tr key={idx} className="hover:bg-slate-50">
                  <td className="p-2 font-bold text-slate-800">{owner.name}</td>
                  <td className="p-2 text-slate-600">{owner.holdingType}</td>
                  <td className="p-2 font-mono font-bold text-[#002642]">{owner.shareRatio}</td>
                  <td className="p-2 font-mono text-slate-600">#{owner.mutationNumber}</td>
                  <td className="p-2 text-slate-600">{owner.entryDate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Section 3: Registration & Mutation Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-[#002642] font-extrabold text-xs text-[#002642] uppercase">
              3. Registration Information
            </div>
            <div className="border border-slate-200 p-3 rounded-xs text-xs space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Registration Number:</span>
                <span className="font-mono font-bold text-slate-800">{property.registration.registrationNumber}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Registration Date:</span>
                <span className="font-semibold text-slate-800">{property.registration.registrationDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Sub-Registrar Office:</span>
                <span className="text-slate-800">{property.registration.subRegistrarOffice}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Transaction Type:</span>
                <span className="font-bold text-[#002642]">{property.registration.transactionType}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Stamp Duty Paid:</span>
                <span className="font-bold text-emerald-700">₹{property.registration.stampDutyPaidINR.toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-[#002642] font-extrabold text-xs text-[#002642] uppercase">
              4. Active Mutation Information
            </div>
            <div className="border border-slate-200 p-3 rounded-xs text-xs space-y-1.5">
              <div className="flex justify-between">
                <span className="text-slate-500">Mutation Application ID:</span>
                <span className="font-mono font-bold text-orange-950">{property.activeMutation.applicationId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Current Status:</span>
                <span className="font-bold text-amber-700">{property.activeMutation.currentStatus}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Active Stage:</span>
                <span className="font-semibold text-slate-800">{property.activeMutation.currentStage}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Application Date:</span>
                <span className="text-slate-800">{property.activeMutation.applicationDate}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Revenue Authority:</span>
                <span className="text-slate-800">{property.activeMutation.revenueOfficer}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Section 5: Document Comparison & Detected Discrepancies */}
        <div className="space-y-3">
          <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-amber-600 font-extrabold text-xs text-amber-950 uppercase">
            5. Cross-Document Comparison &amp; Discrepancy Scanning
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-3 bg-amber-50 border border-amber-300 rounded-xs space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-bold text-amber-950">Area Discrepancy (Sale Deed vs Drone Resurvey)</span>
                <span className="px-2 py-0.5 bg-amber-200 text-amber-950 text-[10px] font-bold rounded-xs">
                  VERIFICATION RECOMMENDED
                </span>
              </div>
              <p className="text-[11px] text-slate-700">
                Registered Deed REG-2018-88492 records 2.45 Ha whereas 2025 SVAMITVA drone boundary polygon computes 2.50 Ha (Delta: 0.05 Ha / +500 sq.m along northern natural nullah).
              </p>
              <div className="text-[10px] text-slate-600 font-semibold pt-1">
                Recommended Step: Request joint boundary survey (Mojani) via TILR.
              </div>
            </div>

            <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-xs space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-bold text-emerald-950">14-Digit ULPIN &amp; Centroid Verification</span>
                <span className="px-2 py-0.5 bg-emerald-200 text-emerald-950 text-[10px] font-bold rounded-xs">
                  LOW DISCREPANCY DETECTED
                </span>
              </div>
              <p className="text-[11px] text-slate-700">
                ULPIN 27712049001234 strictly adheres to DILRMP geo-coordinate standard (Centroid: 21.0764° N, 79.0832° E).
              </p>
            </div>
          </div>
        </div>

        {/* Section 6: Map Information & Property Timeline */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-[#002642] font-extrabold text-xs text-[#002642] uppercase">
              6. Cadastral Map Geometry
            </div>
            <div className="border border-slate-200 p-3 rounded-xs text-xs space-y-1">
              <div>Cadastral Sheet: <strong className="font-mono">{property.cadastralSheetNo}</strong></div>
              <div>Perimeter: <strong>680 meters</strong> (Orthorectified Polygon)</div>
              <div>North Boundary: Perennial irrigation canal buffer</div>
              <div>South Boundary: 6-meter public cart track (Vahiwat Rasta)</div>
              <div>Contiguous Surveys: 123/3 (West) &amp; 123/5 (East)</div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="bg-slate-100 px-3 py-1.5 border-l-4 border-[#002642] font-extrabold text-xs text-[#002642] uppercase">
              7. Historical Timeline Summary
            </div>
            <div className="border border-slate-200 p-3 rounded-xs text-[11px] space-y-1.5">
              <div>• <strong>2018:</strong> Registered Partition Deed (REG-2018-88492)</div>
              <div>• <strong>2020:</strong> Mutation Entry Ferfar 892 Recorded</div>
              <div>• <strong>2021:</strong> Circle Officer Approval &amp; 7/12 Issued</div>
              <div>• <strong>2023:</strong> Partition Entry adding Legal Heir (Ferfar 1042)</div>
              <div>• <strong>2025:</strong> SVAMITVA Drone Resurvey &amp; ULPIN Assigned</div>
              <div>• <strong>2026:</strong> Active Mutation Notice MUT-MH-2026-001245</div>
            </div>
          </div>
        </div>

        {/* Section 8: Sources & Verification Authorities */}
        <div className="border-t-2 border-slate-300 pt-4 text-[10px] text-slate-500 space-y-1">
          <div className="font-bold uppercase text-slate-600">Data Sources:</div>
          <div>1. Department of Land Resources (DoLR), Ministry of Rural Development, Government of India</div>
          <div>2. Revenue and Forest Department, Government of Maharashtra (Mahabhulekh &amp; MahaBhuNaksha)</div>
          <div>3. Inspector General of Registration and Controller of Stamps, Maharashtra (IGR)</div>
          <div>4. Survey of India (CORS Network Demarcation)</div>
          <div className="pt-2 italic text-slate-400">
            End of Preliminary Intelligence Report. For certified copies, please visit respective Sub-Registrar / Tehsil revenue offices.
          </div>
        </div>
      </div>
    </div>
  );
};
