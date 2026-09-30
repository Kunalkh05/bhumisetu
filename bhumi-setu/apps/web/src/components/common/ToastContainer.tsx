import React from 'react';
import { useApp } from '../../context/AppContext';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export const ToastContainer: React.FC = () => {
  const { toasts, removeToast, language } = useApp();

  if (toasts.length === 0) return null;

  return (
    <div 
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md w-full px-4 sm:px-0 pointer-events-none"
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => {
        const isSuccess = toast.type === 'success';
        const isError = toast.type === 'error';
        const isWarning = toast.type === 'warning';

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto p-4 rounded-xl shadow-xl border flex items-start gap-3 transform transition-all duration-300 animate-in slide-in-from-bottom-5 ${
              isSuccess
                ? 'bg-emerald-50 dark:bg-emerald-950/90 border-emerald-300 dark:border-emerald-700 text-emerald-900 dark:text-emerald-100'
                : isError
                ? 'bg-red-50 dark:bg-red-950/90 border-red-300 dark:border-red-700 text-red-900 dark:text-red-100'
                : isWarning
                ? 'bg-amber-50 dark:bg-amber-950/90 border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-100'
                : 'bg-blue-50 dark:bg-blue-950/90 border-blue-300 dark:border-blue-700 text-blue-900 dark:text-blue-100'
            }`}
            role="alert"
          >
            <div className="flex-shrink-0 mt-0.5">
              {isSuccess && <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />}
              {isError && <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />}
              {isWarning && <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />}
              {!isSuccess && !isError && !isWarning && <Info className="w-5 h-5 text-blue-600 dark:text-blue-400" />}
            </div>

            <div className="flex-1 text-xs sm:text-sm font-medium">
              <p>{language === 'en' ? toast.message : (toast.messageHi || toast.message)}</p>
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-0.5 rounded transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
