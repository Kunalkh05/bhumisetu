import React from 'react';
import { Info, CheckCircle2, AlertTriangle, AlertCircle, X } from 'lucide-react';

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'info' | 'success' | 'warning' | 'danger';
  title?: string;
  onDismiss?: () => void;
}

export const Alert: React.FC<AlertProps> = ({
  children,
  variant = 'info',
  title,
  onDismiss,
  className = '',
  ...props
}) => {
  const variantConfig = {
    info: {
      container: 'bg-blue-50/80 border-blue-200 text-blue-900',
      icon: <Info className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />,
      titleColor: 'text-blue-900',
    },
    success: {
      container: 'bg-emerald-50/80 border-emerald-200 text-emerald-900',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />,
      titleColor: 'text-emerald-900',
    },
    warning: {
      container: 'bg-amber-50/80 border-amber-200 text-amber-900',
      icon: <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />,
      titleColor: 'text-amber-900',
    },
    danger: {
      container: 'bg-red-50/80 border-red-200 text-red-900',
      icon: <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />,
      titleColor: 'text-red-900',
    },
  };

  const config = variantConfig[variant];

  return (
    <div
      role="alert"
      className={`
        rounded-xl border p-3.5 text-xs sm:text-sm flex items-start gap-3 transition-colors
        ${config.container}
        ${className}
      `}
      {...props}
    >
      {config.icon}
      
      <div className="flex-1 space-y-0.5 text-left">
        {title && (
          <h5 className={`font-bold leading-tight ${config.titleColor}`}>
            {title}
          </h5>
        )}
        <div className="leading-relaxed opacity-90">
          {children}
        </div>
      </div>

      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-slate-700 p-1 -mr-1 -mt-1 rounded-md transition-colors cursor-pointer"
          aria-label="Dismiss alert"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
