import React, { useState } from 'react';
import { 
  Upload, 
  FileText, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  RefreshCw, 
  ArrowRight, 
  ShieldCheck, 
  FileCheck, 
  Download, 
  Eye, 
  Layers,
  ChevronRight,
  Info,
  Clock
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import { SAMPLE_EXTRACTED_DOCUMENTS } from '../../data/landIntelligenceData';
import { PublicTab } from '../common/GovNavigation';

export const AiDocumentVerification: React.FC<{
  onNavigateTab: (tab: PublicTab) => void;
}> = ({ onNavigateTab }) => {
  const { language, addToast } = useApp();

  const [selectedDocType, setSelectedDocType] = useState<'7_12_EXTRACT' | 'SALE_DEED'>('7_12_EXTRACT');
  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStep, setPipelineStep] = useState<number>(6); // 6 means completed
  const [uploadedFileName, setUploadedFileName] = useState<string>('sample_7_12_extract_besa_123_4.pdf');

  const docTypesList = [
    { id: 'Sale Deed', label: 'Sale Deed / Conveyance', labelHi: 'बैनामा / विक्रय विलेख' },
    { id: '7/12 Extract', label: '7/12 Extract (Saat Bara)', labelHi: '७/१२ (सात-बारा) उद्धरण' },
    { id: 'Record of Rights', label: 'Record of Rights (RoR / RTC)', labelHi: 'अधिकार अभिलेख (खतौनी)' },
    { id: 'Khasra/Khatauni', label: 'Khasra / Khatauni', labelHi: 'खसरा / खतौनी नकल' },
    { id: 'Property Card', label: 'Property Card / Sampatti Patra', labelHi: 'प्रॉपर्टी कार्ड (स्वामित्व)' },
    { id: 'Mutation Document', label: 'Mutation Document (Ferfar)', labelHi: 'नामांतरण आदेश (फेरफार)' },
    { id: 'Registration Document', label: 'Registration Index-II', labelHi: 'पंजीयन सूचिपत्र (Index-II)' },
    { id: 'Other land documents', label: 'Other Land Documents', labelHi: 'अन्य राजस्व दस्तावेज' },
  ];

  const currentData = SAMPLE_EXTRACTED_DOCUMENTS[selectedDocType];

  const handleSimulateAnalysis = (type: '7_12_EXTRACT' | 'SALE_DEED', filename: string) => {
    setSelectedDocType(type);
    setUploadedFileName(filename);
    setIsProcessing(true);
    setPipelineStep(1);

    const interval = setInterval(() => {
      setPipelineStep(prev => {
        if (prev >= 6) {
          clearInterval(interval);
          setIsProcessing(false);
          addToast({
            type: 'success',
            message: 'AI Document OCR & Cross-Comparison Analysis Completed.',
            messageHi: 'दस्तावेज विश्लेषण पूर्ण हुआ।'
          });
          return 6;
        }
        return prev + 1;
      });
    }, 350);
  };

  const pipelineStages = [
    { num: 1, label: 'Upload Document', labelHi: 'दस्तावेज अपलोड' },
    { num: 2, label: 'OCR Processing', labelHi: 'ओसीआर प्रोसेसिंग' },
    { num: 3, label: 'Information Extraction', labelHi: 'सूचना निष्कर्षण' },
    { num: 4, label: 'Cross-Comparison', labelHi: 'पारस्परिक तुलना' },
    { num: 5, label: 'Discrepancy Detection', labelHi: 'विसंगति पहचान' },
    { num: 6, label: 'Preliminary Report', labelHi: 'प्राथमिक रिपोर्ट' },
  ];

  return (
    <div className="space-y-6 text-left">
      {/* Title & Preliminary Purpose */}
      <div className="bg-[#002642] text-white p-5 rounded-xs border-b-3 border-[#f37021] flex flex-wrap justify-between items-center gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg sm:text-xl font-bold">
              {language === 'en' ? 'AI Document Verification' : 'एआई भू-दस्तावेज सत्यापन'}
            </h2>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-[#138808] text-white">
              AI VISION OCR
            </span>
          </div>
          <p className="text-xs text-slate-300 mt-1 max-w-3xl">
            {language === 'en'
              ? 'Upload land deeds, 7/12 extracts, or mutation records to extract key parameters and detect cross-document inconsistencies.'
              : 'भू-विलेख, ७/१२ उद्धरण अथवा नामांतरण प्रपत्र अपलोड कर मुख्य पैरामीटर निकालें एवं दस्तावेजों के मध्य अंतर की जांच करें।'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => handleSimulateAnalysis('7_12_EXTRACT', 'sample_7_12_extract_besa_123_4.pdf')}
            className="px-3 py-1.5 bg-white/10 hover:bg-white/20 text-white font-bold text-xs rounded-xs border border-white/25 transition-colors"
          >
            Sample 7/12 Extract
          </button>
          <button
            onClick={() => handleSimulateAnalysis('SALE_DEED', 'registered_sale_deed_nagpur_2018.pdf')}
            className="px-3 py-1.5 bg-[#f37021] hover:bg-[#d95a10] text-white font-bold text-xs rounded-xs transition-colors"
          >
            Sample Sale Deed
          </button>
        </div>
      </div>

      {/* Mandatory Pipeline Workflow Visualization */}
      <div className="bg-white border border-slate-300 rounded-xs p-4 shadow-2xs">
        <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">
          {language === 'en' ? 'AI Verification Pipeline Workflow:' : 'एआई सत्यापन प्रक्रिया:'}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
          {pipelineStages.map((stage) => {
            const isCompleted = pipelineStep >= stage.num;
            const isCurrent = pipelineStep === stage.num && isProcessing;

            return (
              <div
                key={stage.num}
                className={`p-2.5 rounded-xs border text-center transition-all ${
                  isCurrent 
                    ? 'bg-amber-100 border-[#f37021] text-[#c2410c] font-bold shadow-xs animate-pulse'
                    : isCompleted 
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-900 font-semibold' 
                    : 'bg-slate-50 border-slate-200 text-slate-400'
                }`}
              >
                <div className="text-[10px] font-mono">Stage 0{stage.num}</div>
                <div className="text-xs mt-0.5 font-bold leading-tight">
                  {language === 'en' ? stage.label : stage.labelHi}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Upload Zone & Document Picker */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 bg-white border border-slate-300 rounded-xs p-5 shadow-xs space-y-4">
          <h3 className="font-bold text-sm text-[#002642] uppercase tracking-wide border-b border-slate-200 pb-2">
            {language === 'en' ? 'Upload Land Document' : 'दस्तावेज अपलोड करें'}
          </h3>

          <div>
            <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
              Document Category
            </label>
            <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
              {docTypesList.map((doc, idx) => (
                <label
                  key={idx}
                  className="flex items-center gap-2 p-2 hover:bg-slate-50 border border-slate-200 rounded-xs cursor-pointer text-xs"
                >
                  <input
                    type="radio"
                    name="docTypeSelect"
                    checked={
                      (selectedDocType === '7_12_EXTRACT' && doc.id.includes('7/12')) ||
                      (selectedDocType === 'SALE_DEED' && doc.id.includes('Sale Deed'))
                    }
                    onChange={() => {
                      if (doc.id.includes('Sale Deed')) {
                        handleSimulateAnalysis('SALE_DEED', 'registered_sale_deed_nagpur_2018.pdf');
                      } else {
                        handleSimulateAnalysis('7_12_EXTRACT', 'sample_7_12_extract_besa_123_4.pdf');
                      }
                    }}
                    className="text-[#002642] focus:ring-[#002642]"
                  />
                  <span>{language === 'en' ? doc.label : doc.labelHi}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Interactive Drag & Drop Box */}
          <div 
            onClick={() => handleSimulateAnalysis(selectedDocType === '7_12_EXTRACT' ? 'SALE_DEED' : '7_12_EXTRACT', 'user_uploaded_land_record.pdf')}
            className="border-2 border-dashed border-slate-300 hover:border-[#002642] p-6 rounded-xs text-center cursor-pointer bg-slate-50 hover:bg-blue-50/50 transition-colors"
          >
            <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <div className="font-bold text-xs text-[#002642]">
              Click to select or drag document PDF / Image
            </div>
            <div className="text-[10px] text-slate-500 mt-1">
              Supports scanned PDFs, JPEG, PNG, TIFF up to 25 MB
            </div>
            <span className="inline-block mt-3 px-3 py-1 bg-[#002642] text-white text-[10px] font-bold rounded-xs">
              Simulate File Upload
            </span>
          </div>

          <div className="p-3 bg-amber-50 border border-amber-200 rounded-xs text-[10px] text-amber-900 leading-relaxed">
            <strong>Privacy Guarantee:</strong> Documents uploaded in this prototype are processed entirely in-memory and are never stored permanently on central servers.
          </div>
        </div>

        {/* Results: Extracted Information & Detected Discrepancies */}
        <div className="lg:col-span-8 space-y-5">
          {/* Active File Header */}
          <div className="bg-white border border-slate-300 rounded-xs p-4 shadow-xs flex flex-wrap justify-between items-center gap-3">
            <div>
              <span className="text-[10px] uppercase font-bold text-slate-400">Analyzed Document</span>
              <div className="font-bold text-sm text-[#002642] mt-0.5">
                {currentData.documentType}
              </div>
              <div className="text-[11px] text-slate-500 font-mono">
                Source File: {uploadedFileName}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <span className="text-[10px] uppercase font-bold text-slate-400">OCR Confidence</span>
                <div className="font-extrabold text-sm text-emerald-700">
                  {currentData.confidenceScore}% High Accuracy
                </div>
              </div>
              <button
                onClick={() => handleSimulateAnalysis(selectedDocType, uploadedFileName)}
                className="p-2 rounded-xs bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                title="Rerun OCR"
              >
                <RefreshCw className={`w-4 h-4 ${isProcessing ? 'animate-spin text-[#f37021]' : ''}`} />
              </button>
            </div>
          </div>

          {/* Section: Extracted Information */}
          <div className="bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-[#138808]" />
                <span>Extracted Information (OCR Output)</span>
              </h3>
              <span className="text-[10px] text-slate-500 font-semibold">
                {currentData.extractedFields.length} Attributes Extracted
              </span>
            </div>

            <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
              {currentData.extractedFields.map((field, idx) => (
                <div key={idx} className="p-2.5 bg-slate-50 border border-slate-200 rounded-xs">
                  <div className="flex justify-between items-center">
                    <span className="text-[10px] font-bold text-slate-400 uppercase">{field.label}</span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.2 rounded-xs ${
                      field.status === 'Discrepancy' 
                        ? 'bg-amber-100 text-amber-900 border border-amber-300' 
                        : 'bg-emerald-100 text-emerald-900'
                    }`}>
                      {field.status}
                    </span>
                  </div>
                  <div className="font-bold text-xs text-slate-800 mt-1">
                    {field.value}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section: Detected Discrepancies */}
          <div className="bg-white border border-slate-300 rounded-xs shadow-xs overflow-hidden">
            <div className="bg-[#f8fafc] border-b border-slate-200 px-4 py-3 flex justify-between items-center">
              <h3 className="font-extrabold text-sm text-[#002642] uppercase tracking-wide flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-[#f37021]" />
                <span>Detected Discrepancies (Cross-Document Match)</span>
              </h3>
              <span className="px-2 py-0.5 bg-amber-100 text-amber-900 border border-amber-300 rounded-xs text-[10px] font-bold">
                {currentData.discrepancies.length} Flagged
              </span>
            </div>

            <div className="p-4 space-y-3 text-xs">
              {currentData.discrepancies.map((disc, idx) => (
                <div key={idx} className="p-3.5 bg-amber-50/70 border-l-4 border-amber-500 rounded-xs space-y-2">
                  <div className="flex justify-between items-start">
                    <div className="font-bold text-amber-950 text-xs">
                      {disc.field}
                    </div>
                    <span className="px-2 py-0.5 rounded-xs text-[9px] font-black uppercase tracking-wider bg-amber-200 text-amber-950">
                      {disc.severity} VARIANCE
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] pt-1 border-t border-amber-200">
                    <div>
                      <span className="text-slate-500">Value in Uploaded Document:</span>
                      <div className="font-bold text-slate-800">{disc.valueInDoc}</div>
                    </div>
                    <div>
                      <span className="text-slate-500">Value in Digital Registry:</span>
                      <div className="font-bold text-slate-800">{disc.valueInRegistry}</div>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-600 italic">
                    {disc.comment}
                  </p>
                </div>
              ))}

              <div className="pt-2 flex justify-end gap-2">
                <button
                  onClick={() => onNavigateTab('RISK_ANALYSIS')}
                  className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white font-bold text-xs rounded-xs flex items-center gap-1.5 transition-colors"
                >
                  <span>Review in 12-Point Risk Analysis</span>
                  <ChevronRight className="w-3.5 h-3.5 text-[#f37021]" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
