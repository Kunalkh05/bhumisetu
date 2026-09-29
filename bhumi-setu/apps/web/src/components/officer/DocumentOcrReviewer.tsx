import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  FileText, 
  CheckCircle, 
  AlertTriangle, 
  Edit3, 
  Eye, 
  Upload, 
  ShieldCheck, 
  Check, 
  X, 
  RotateCcw,
  Sparkles,
  Maximize2,
  FileSearch,
  ExternalLink,
  History
} from 'lucide-react';
import { ExtractedField, DocumentRecord } from '../../types';

export const DocumentOcrReviewer: React.FC = () => {
  const { selectedCase, correctOcrField, confirmOcrField, currentUser, language, addToast } = useApp();

  const [selectedDocId, setSelectedDocId] = useState<string>(selectedCase.documents[0]?.id || '');
  const [selectedFieldId, setSelectedFieldId] = useState<string>('FLD-03');
  const [editingValue, setEditingValue] = useState<string>('');
  const [isEditing, setIsEditing] = useState(false);

  const doc = selectedCase.documents.find(d => d.id === selectedDocId) || selectedCase.documents[0];
  const activeField = doc?.extractedFields.find(f => f.id === selectedFieldId);

  const handleStartEdit = (field: ExtractedField) => {
    setSelectedFieldId(field.id);
    setEditingValue(field.extractedValue);
    setIsEditing(true);
  };

  const handleSaveCorrection = () => {
    if (!doc || !selectedFieldId) return;
    correctOcrField(selectedCase.id, doc.id, selectedFieldId, editingValue);
    setIsEditing(false);
  };

  const handleConfirmDirect = (fieldId: string) => {
    if (!doc) return;
    confirmOcrField(selectedCase.id, doc.id, fieldId);
  };

  const handleSimulateUpload = () => {
    addToast({
      type: 'info',
      message: 'New document (Joint Measurement Survey Map) uploaded. Asynchronous Devanagari OCR enqueued.',
      messageHi: 'नया भू-अभिलेख अपलोड किया गया। देवनागरी ओसीआर प्रक्रिया प्रारंभ।',
    });
  };

  if (!doc) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12 text-center text-slate-500">
        <FileText className="w-12 h-12 mx-auto mb-2 text-slate-400" />
        <p>{language === 'en' ? 'No uploaded documents available for this case.' : 'इस प्रकरण हेतु कोई दस्तावेज उपलब्ध नहीं है।'}</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Header Bar */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <FileSearch className="w-5 h-5 text-blue-700 dark:text-blue-400" />
              {language === 'en' ? 'Document Digitization & Human-in-the-Loop OCR Verification' : 'दस्तावेज डिजिटलीकरण एवं ओसीआर मानवीय सत्यापन'}
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-300">
              Script: {doc.detectedScript}
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en' 
              ? 'Multi-script OCR extraction with bounding box coordinates and confidence threshold routing (Q4 Compliance).'
              : 'बाउंडिंग बॉक्स निर्देशांक एवं विश्वास सीमा आधारित बहुभाषी ओसीआर सत्यापन प्रणाली।'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Document Selector */}
          <select
            value={selectedDocId}
            onChange={(e) => setSelectedDocId(e.target.value)}
            className="text-xs font-bold bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-800 dark:text-slate-200"
          >
            {selectedCase.documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title} ({d.fileSizeFormatted})
              </option>
            ))}
          </select>

          <button
            onClick={handleSimulateUpload}
            className="px-3 py-2 bg-blue-800 hover:bg-blue-900 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>{language === 'en' ? 'Upload Record' : 'दस्तावेज अपलोड करें'}</span>
          </button>
        </div>
      </div>

      {/* Main Split Interface (Document Canvas Preview on Left, Fields Extracted on Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 7 Cols: Simulated Scanned Document Canvas */}
        <div className="lg:col-span-7 bg-slate-900 rounded-2xl border border-slate-800 shadow-xl overflow-hidden flex flex-col justify-between">
          <div className="p-3.5 bg-slate-950/80 border-b border-slate-800 flex justify-between items-center text-xs text-slate-300">
            <span className="font-bold truncate max-w-sm">{doc.filename} ({doc.fileSizeFormatted})</span>
            <span className="text-[11px] text-slate-400 font-mono">Checksum: {doc.checksum.substring(0, 16)}...</span>
          </div>

          {/* Scanned 7/12 Land Record Visual with Interactive Bounding Box Highlights */}
          <div className="relative p-6 bg-amber-50/95 dark:bg-slate-950 min-h-[500px] flex items-center justify-center overflow-hidden font-serif">
            {/* Paper Document Background Texture & Government Watermark */}
            <div className="w-full max-w-lg bg-[#fdfbf7] dark:bg-slate-900 p-6 rounded-lg shadow-2xl border border-amber-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 relative space-y-4 select-none">
              
              {/* Maharashtra Gov 7/12 Header */}
              <div className="text-center pb-3 border-b-2 border-slate-800 dark:border-slate-600">
                <div className="text-[11px] font-bold tracking-widest text-slate-700 dark:text-slate-300 uppercase">
                  महाराष्ट्र शासन - महसूल व वन विभाग
                </div>
                <h3 className="text-base font-black tracking-wide mt-0.5">
                  गाव नमुना सात (७) / बारा (१२) - अधिकार अभिलेख पत्रक
                </h3>
                <div className="flex justify-between text-[11px] mt-1 font-sans text-slate-600 dark:text-slate-400">
                  <span><strong>गाव:</strong> शिंदॆवाडी</span>
                  <span><strong>तालुका:</strong> हवेली</span>
                  <span><strong>जिल्हा:</strong> पुणे</span>
                </div>
              </div>

              {/* Document Fields Grid Layout with Bounding Boxes */}
              <div className="grid grid-cols-2 gap-3 text-xs font-sans">
                {/* Field 1: Gat Number */}
                <div 
                  onClick={() => setSelectedFieldId('FLD-01')}
                  className={`p-2 rounded border transition-all cursor-pointer ${
                    selectedFieldId === 'FLD-01'
                      ? 'ring-2 ring-blue-600 bg-blue-100/60 dark:bg-blue-950/60 border-blue-600'
                      : 'border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-slate-100'
                  }`}
                >
                  <span className="text-[10px] text-slate-500 block">भूमापन क्रमांक / गट क्र.</span>
                  <span className="font-bold font-mono text-sm text-blue-900 dark:text-blue-200">गट क्र. १४२/अ</span>
                  <span className="text-[9px] text-emerald-700 font-bold block mt-0.5">Confidence 0.98 (Auto Accepted)</span>
                </div>

                {/* Field 4: Total Area */}
                <div 
                  onClick={() => setSelectedFieldId('FLD-04')}
                  className={`p-2 rounded border transition-all cursor-pointer ${
                    selectedFieldId === 'FLD-04'
                      ? 'ring-2 ring-blue-600 bg-blue-100/60 dark:bg-blue-950/60 border-blue-600'
                      : 'border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-slate-100'
                  }`}
                >
                  <span className="text-[10px] text-slate-500 block">एकूण क्षेत्र (हे.आर)</span>
                  <span className="font-bold text-slate-900 dark:text-slate-100">२.४५ हेक्टर</span>
                  <span className="text-[9px] text-amber-600 font-bold block mt-0.5">Confidence 0.92 (Review)</span>
                </div>
              </div>

              {/* Khatedar Owners Section (Field 2 & 3) */}
              <div className="p-3 border border-slate-300 dark:border-slate-700 rounded-lg space-y-2 font-sans">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block">
                  खातेदाराचे नाव (Occupant / Landowners)
                </span>

                <div 
                  onClick={() => setSelectedFieldId('FLD-02')}
                  className={`p-2 rounded border transition-all cursor-pointer ${
                    selectedFieldId === 'FLD-02'
                      ? 'ring-2 ring-blue-600 bg-blue-100/60 dark:bg-blue-950/60 border-blue-600'
                      : 'border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-900 dark:text-slate-100">१. तुकाराम बापू जाधव (६०%)</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800 font-bold">0.96 Match</span>
                  </div>
                </div>

                <div 
                  onClick={() => setSelectedFieldId('FLD-03')}
                  className={`p-2 rounded border transition-all cursor-pointer relative ${
                    selectedFieldId === 'FLD-03'
                      ? 'ring-2 ring-amber-500 bg-amber-100/80 dark:bg-amber-950/80 border-amber-500'
                      : 'border-amber-300 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/30'
                  }`}
                >
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-bold text-slate-900 dark:text-slate-100">२. शांताबाई तुकाराम जाधव (४०%)</span>
                    <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 font-bold">0.74 Needs Review</span>
                  </div>
                </div>
              </div>

              {/* Encumbrances & Bank Charge (Field 5) */}
              <div 
                onClick={() => setSelectedFieldId('FLD-05')}
                className={`p-3 rounded border transition-all cursor-pointer font-sans ${
                  selectedFieldId === 'FLD-05'
                    ? 'ring-2 ring-blue-600 bg-blue-100/60 dark:bg-blue-950/60 border-blue-600'
                    : 'border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                <span className="text-[10px] font-bold text-slate-500 block">इतर हक्क व बोजा (Encumbrances)</span>
                <span className="text-xs text-slate-800 dark:text-slate-200 font-medium">बँक ऑफ महाराष्ट्र शाखा खेड कृषी कर्ज रु. ४,५०,०००/-</span>
                <span className="text-[9px] text-amber-600 font-bold block mt-0.5">Confidence 0.68 (Pending Human Sign-off)</span>
              </div>
            </div>
          </div>

          <div className="p-3 bg-slate-950 border-t border-slate-800 flex justify-between text-xs text-slate-400">
            <span>OCR Engine: Tesseract + Google Vision Devanagari Model v3.2</span>
            <span>Resolution: 300 DPI</span>
          </div>
        </div>

        {/* Right 5 Cols: Extracted Fields Review & Correction Panel */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm p-5 space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-center pb-3 border-b border-slate-100 dark:border-slate-800">
              <h3 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {language === 'en' ? 'Extracted Fields Ledger' : 'निष्कर्षित ओसीआर फ़ील्ड'}
              </h3>
              <span className="text-xs font-bold px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200">
                {doc.extractedFields.length} Fields
              </span>
            </div>

            {/* Threshold Legend (Q4 Requirement) */}
            <div className="my-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-600 dark:text-slate-300 space-y-1">
              <span className="font-bold block text-slate-800 dark:text-slate-200">Statutory Confidence Thresholds:</span>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span><strong>≥ 0.95:</strong> Auto-Accepted (Statutory Valid)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span><strong>0.60 – 0.94:</strong> Mandatory Officer Review</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                <span><strong>&lt; 0.60:</strong> Discard &amp; Manual Entry Required</span>
              </div>
            </div>

            {/* Fields List */}
            <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
              {doc.extractedFields.map((field) => {
                const isSelected = selectedFieldId === field.id;
                const isPending = field.reviewState === 'PENDING_REVIEW';
                const isAuto = field.reviewState === 'AUTO_ACCEPTED';
                const isCorrected = field.reviewState === 'CORRECTED';
                const isConfirmed = field.reviewState === 'CONFIRMED';

                return (
                  <div
                    key={field.id}
                    onClick={() => {
                      setSelectedFieldId(field.id);
                      setIsEditing(false);
                    }}
                    className={`p-3 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50/50 dark:bg-blue-950/40 ring-1 ring-blue-500'
                        : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 bg-white dark:bg-slate-800/30'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-[10px] uppercase font-bold text-slate-500">
                          {language === 'en' ? field.fieldLabel : field.fieldLabelHi}
                        </span>
                        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                          {field.extractedValue}
                        </h4>
                      </div>

                      <div className="text-right">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isAuto ? 'bg-emerald-100 text-emerald-800' :
                          isPending ? 'bg-amber-100 text-amber-800' :
                          isCorrected ? 'bg-purple-100 text-purple-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {field.reviewState.replace(/_/g, ' ')}
                        </span>
                        <span className="block text-[10px] text-slate-500 font-mono mt-0.5">
                          Conf: {field.confidence.toFixed(2)}
                        </span>
                      </div>
                    </div>

                    {/* Correction / Confirm Controls when selected */}
                    {isSelected && (
                      <div className="mt-3 pt-2.5 border-t border-slate-200 dark:border-slate-700 space-y-2">
                        {isEditing ? (
                          <div className="space-y-2">
                            <input
                              type="text"
                              value={editingValue}
                              onChange={(e) => setEditingValue(e.target.value)}
                              className="w-full text-xs p-2 rounded-lg border border-blue-500 bg-white dark:bg-slate-800 font-medium"
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                onClick={() => setIsEditing(false)}
                                className="px-2.5 py-1 text-xs text-slate-600 dark:text-slate-300 font-bold"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={handleSaveCorrection}
                                className="px-3 py-1 bg-blue-800 hover:bg-blue-900 text-white rounded-lg text-xs font-bold"
                              >
                                Save Correction
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => handleStartEdit(field)}
                              className="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 text-slate-800 dark:text-slate-200 text-xs font-bold flex items-center gap-1"
                            >
                              <Edit3 className="w-3 h-3" />
                              <span>{language === 'en' ? 'Edit / Correct' : 'संशोधित करें'}</span>
                            </button>

                            {isPending && (
                              <button
                                onClick={() => handleConfirmDirect(field.id)}
                                className="px-3 py-1 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold flex items-center gap-1"
                              >
                                <Check className="w-3 h-3" />
                                <span>{language === 'en' ? 'Confirm Value' : 'पुष्टि करें'}</span>
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-3 bg-blue-50 dark:bg-blue-950/40 rounded-xl border border-blue-200 dark:border-blue-800 text-[11px] text-blue-900 dark:text-blue-200 flex items-center justify-between">
            <span>Verified edits are automatically signed and appended to immutable event log.</span>
            <ShieldCheck className="w-4 h-4 text-blue-700 flex-shrink-0" />
          </div>
        </div>
      </div>
    </div>
  );
};
