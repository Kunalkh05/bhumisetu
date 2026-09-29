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
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6 animate-in fade-in">
      {/* Top Header */}
      <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-wrap justify-between items-center gap-4">
        <div>
          <h2 className="text-lg font-black text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            {language === 'en' ? 'Bulk Land Records Ingestion & Partial Commit Engine (Req 30)' : 'थोक भू-अभिलेख आयात एवं आंशिक स्वीकृति इंजन'}
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {language === 'en'
              ? 'District-scale CSV/Excel ingestion. Valid rows commit directly; invalid rows generate downloadable error spreadsheets.'
              : 'जिला-स्तरीय भू-अभिलेख आयात। वैध पंक्तियों की सीधी प्रविष्टि एवं त्रुटिपूर्ण पंक्तियों की पृथक रिपोर्ट।'}
          </p>
        </div>

        <button
          onClick={handleSimulateNewCsv}
          disabled={isSimulatingUpload}
          className="px-4 py-2 bg-blue-800 hover:bg-blue-900 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all"
        >
          <UploadCloud className="w-4 h-4" />
          <span>{isSimulatingUpload ? 'Parsing CSV...' : 'Upload New CSV Batch'}</span>
        </button>
      </div>

      {/* Staged Batch Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Total Rows Uploaded</span>
          <div className="text-3xl font-black text-slate-900 dark:text-slate-100 font-mono mt-1">
            {currentBatch.totalRows}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Batch: {currentBatch.batchNumber}</span>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Valid Rows (Pass Schema)</span>
          <div className="text-3xl font-black text-emerald-600 dark:text-emerald-400 font-mono mt-1">
            {currentBatch.totalRows - currentBatch.rejectedRows}
          </div>
          <span className="text-xs text-emerald-600 font-semibold mt-1 block">Ready for commit</span>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Error Rows (Rejected)</span>
          <div className="text-3xl font-black text-red-600 dark:text-red-400 font-mono mt-1">
            {currentBatch.rejectedRows}
          </div>
          <span className="text-xs text-red-600 font-semibold mt-1 block">Requires manual correction</span>
        </div>

        <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Committed to Database</span>
          <div className="text-3xl font-black text-blue-700 dark:text-blue-400 font-mono mt-1">
            {currentBatch.committedRows} / {currentBatch.totalRows - currentBatch.rejectedRows}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Status: {currentBatch.status}</span>
        </div>
      </div>

      {/* Partial Commit Action Bar */}
      <div className="bg-blue-50 dark:bg-blue-950/60 p-4 rounded-2xl border border-blue-200 dark:border-blue-800 flex flex-wrap justify-between items-center gap-4">
        <div className="text-xs text-blue-900 dark:text-blue-200">
          <strong>Partial Commit Policy:</strong> Valid rows can be committed immediately without being blocked by invalid rows in the same spreadsheet.
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
            className="px-3 py-2 bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700 hover:bg-slate-50 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Error Rows CSV</span>
          </button>

          <button
            onClick={handleExecuteCommit}
            disabled={isProcessing || currentBatch.committedRows === (currentBatch.totalRows - currentBatch.rejectedRows)}
            className="px-4 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all"
          >
            <Play className="w-3.5 h-3.5" />
            <span>{isProcessing ? 'Committing...' : 'Commit Valid Rows Now'}</span>
          </button>
        </div>
      </div>

      {/* Row-Level Inspection Table */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden space-y-4 p-5">
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Table className="w-4 h-4 text-blue-700" />
          <span>{language === 'en' ? 'Staged Data Records Validation Breakdown' : 'प्रस्तुत डेटा रिकॉर्ड सत्यापन विवरण'}</span>
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-b border-slate-200 dark:border-slate-700">
                <th className="py-2.5 px-3">Row #</th>
                <th className="py-2.5 px-3">Survey Gat</th>
                <th className="py-2.5 px-3">Khatedar Name</th>
                <th className="py-2.5 px-3">Extent (Ha)</th>
                <th className="py-2.5 px-3">Share</th>
                <th className="py-2.5 px-3">Validation Result</th>
                <th className="py-2.5 px-3">Error / Defect Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono">
              {currentBatch.rows.map((row) => (
                <tr key={row.rowNumber} className={row.status === 'REJECTED' ? 'bg-red-50/50 dark:bg-red-950/20' : ''}>
                  <td className="py-2.5 px-3 font-bold text-slate-700 dark:text-slate-300">Row {row.rowNumber}</td>
                  <td className="py-2.5 px-3">{row.surveyNumber}</td>
                  <td className="py-2.5 px-3 font-sans text-slate-900 dark:text-slate-100">{row.ownerName}</td>
                  <td className="py-2.5 px-3">{row.extentHa}</td>
                  <td className="py-2.5 px-3">{row.share}</td>
                  <td className="py-2.5 px-3 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      row.status === 'REJECTED' ? 'bg-red-600 text-white' : 'bg-emerald-600 text-white'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 font-sans text-red-700 dark:text-red-300 font-medium">
                    {row.errorMessage || 'None — Ready to commit'}
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
