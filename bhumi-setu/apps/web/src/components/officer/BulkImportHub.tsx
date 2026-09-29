import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { 
  UploadCloud, 
  FileSpreadsheet, 
  CheckCircle2, 
  AlertTriangle, 
  Download, 
  Play, 
  RotateCcw,
  Check,
  X,
  FileCheck2,
  Table,
  Layers
} from 'lucide-react';
import { ImportBatch } from '../../types';
import { MOCK_IMPORT_BATCHES } from '../../data/mockData';

export const BulkImportHub: React.FC = () => {
  const { language, addToast } = useApp();
  const [batches, setBatches] = useState<ImportBatch[]>(MOCK_IMPORT_BATCHES);
  const currentBatch = batches[0];
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSimulatingUpload, setIsSimulatingUpload] = useState(false);

  const handleSimulateNewCsv = () => {
    setIsSimulatingUpload(true);
    setTimeout(() => {
      setIsSimulatingUpload(false);
      addToast({
        type: 'success',
        message: 'File "khed_tehsil_nh48_revised_parcels.csv" staged for validation.',
        messageHi: 'सीवीएस फ़ाइल सत्यापन हेतु लोड की गई।',
      });
    }, 1200);
  };

  const handleExecuteCommit = () => {
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      setBatches(prev => prev.map((b, idx) => idx === 0 ? {
        ...b,
        committedRows: b.totalRows - b.rejectedRows,
        status: 'COMPLETED'
      } : b));
      addToast({
        type: 'success',
        message: `Committed ${currentBatch.totalRows - currentBatch.rejectedRows} valid parcel & ownership rows. Skipped ${currentBatch.rejectedRows} error rows.`,
        messageHi: `${currentBatch.totalRows - currentBatch.rejectedRows} वैध पंक्तियां डेटाबेस में सफलतापूर्वक दर्ज।`,
      });
    }, 1800);
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-6 animate-in fade-in">
      {/* Top Header */}
      <div className="gov-surface-card p-5 sm:p-6 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded-xs text-[10px] font-bold bg-[#002642] text-white">
              Data Ingestion Service
            </span>
            <span className="text-[11px] text-slate-500 font-mono">
              RFC 4180 CSV / XLSX Stream Ingest
            </span>
          </div>
          <h2 className="text-lg font-bold text-[#002642] flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
            <span>{language === 'en' ? 'Bulk Land Records Ingestion & Partial Commit Engine' : 'थोक भू-अभिलेख आयात एवं आंशिक स्वीकृति इंजन'}</span>
          </h2>
          <p className="text-xs text-slate-600 mt-1 max-w-3xl">
            {language === 'en'
              ? 'District-scale CSV/Excel ingestion. Valid rows commit directly; invalid rows generate downloadable error spreadsheets.'
              : 'जिला-स्तरीय भू-अभिलेख आयात। वैध पंक्तियों की सीधी प्रविष्टि एवं त्रुटिपूर्ण पंक्तियों की पृथक रिपोर्ट।'}
          </p>
        </div>

        <button
          onClick={handleSimulateNewCsv}
          disabled={isSimulatingUpload}
          className="px-4 py-2 bg-[#002642] hover:bg-[#0b3866] text-white rounded-sm text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-50"
        >
          <UploadCloud className="w-4 h-4" />
          <span>{isSimulatingUpload ? 'Parsing CSV...' : 'Upload New CSV Batch'}</span>
        </button>
      </div>

      {/* Staged Batch Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="gov-surface-card p-5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Total Rows Uploaded</span>
          <div className="text-2xl font-black text-slate-900 font-mono mt-1">
            {currentBatch.totalRows}
          </div>
          <span className="text-xs text-slate-500 mt-1 block font-mono">Batch: {currentBatch.batchNumber}</span>
        </div>

        <div className="gov-surface-card p-5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Valid Rows (Pass Schema)</span>
          <div className="text-2xl font-black text-emerald-600 font-mono mt-1">
            {currentBatch.totalRows - currentBatch.rejectedRows}
          </div>
          <span className="text-xs text-emerald-700 font-semibold mt-1 block">Ready for commit</span>
        </div>

        <div className="gov-surface-card p-5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Error Rows (Rejected)</span>
          <div className="text-2xl font-black text-red-600 font-mono mt-1">
            {currentBatch.rejectedRows}
          </div>
          <span className="text-xs text-red-700 font-semibold mt-1 block">Requires manual correction</span>
        </div>

        <div className="gov-surface-card p-5">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">Committed to Database</span>
          <div className="text-2xl font-black text-[#002642] font-mono mt-1">
            {currentBatch.committedRows} / {currentBatch.totalRows - currentBatch.rejectedRows}
          </div>
          <span className="text-xs text-slate-500 mt-1 block font-mono">Status: {currentBatch.status}</span>
        </div>
      </div>

      {/* Partial Commit Action Bar */}
      <div className="gov-surface-card p-4 bg-slate-50 border-slate-200 flex flex-wrap justify-between items-center gap-4">
        <div className="text-xs text-slate-700">
          <strong className="text-[#002642]">Partial Commit Policy:</strong> Valid rows can be committed immediately without being blocked by invalid rows in the same spreadsheet.
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              addToast({
                type: 'info',
                message: 'Downloaded "error_rows_batch_421.csv" containing 2 flagged records with statutory defect reasons.',
                messageHi: 'त्रुटिपूर्ण पंक्तियों की रिपोर्ट डाउनलोड की गई।',
              });
            }}
            className="px-3 py-2 bg-white text-slate-700 border border-slate-300 hover:bg-slate-100 rounded-sm text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Error Rows CSV</span>
          </button>

          <button
            onClick={handleExecuteCommit}
            disabled={isProcessing || currentBatch.committedRows === (currentBatch.totalRows - currentBatch.rejectedRows)}
            className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white rounded-sm text-xs font-bold flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{isProcessing ? 'Committing...' : 'Commit Valid Rows Now'}</span>
          </button>
        </div>
      </div>

      {/* Row-Level Inspection Table */}
      <div className="gov-surface-card overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-[#002642] flex items-center gap-2">
            <Table className="w-4 h-4 text-[#002642]" />
            <span>{language === 'en' ? 'Staged Data Records Validation Breakdown' : 'प्रस्तुत डेटा रिकॉर्ड सत्यापन विवरण'}</span>
          </h3>
          <span className="text-xs text-slate-500 font-mono">{currentBatch.rows.length} records staged</span>
        </div>

        <div className="overflow-x-auto">
          <table className="gov-table-2026">
            <thead>
              <tr>
                <th className="py-2.5 px-3">Row #</th>
                <th className="py-2.5 px-3">Survey Gat</th>
                <th className="py-2.5 px-3">Khatedar Name</th>
                <th className="py-2.5 px-3">Extent (Ha)</th>
                <th className="py-2.5 px-3">Share</th>
                <th className="py-2.5 px-3">Validation Result</th>
                <th className="py-2.5 px-3">Error / Defect Reason</th>
              </tr>
            </thead>
            <tbody>
              {currentBatch.rows.map((row) => (
                <tr key={row.rowNumber} className={row.status === 'REJECTED' ? 'bg-red-50/40' : 'hover:bg-slate-50/80'}>
                  <td className="py-2.5 px-3 font-mono font-bold text-slate-700">Row {row.rowNumber}</td>
                  <td className="py-2.5 px-3 font-mono">{row.surveyNumber}</td>
                  <td className="py-2.5 px-3 font-medium text-slate-900">{row.ownerName}</td>
                  <td className="py-2.5 px-3 font-mono">{row.extentHa}</td>
                  <td className="py-2.5 px-3 font-mono">{row.share}</td>
                  <td className="py-2.5 px-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-xs text-[10px] font-bold ${
                      row.status === 'REJECTED' ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-red-700 font-medium">
                    {row.errorMessage || <span className="text-slate-400 font-normal">None — Ready to commit</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
