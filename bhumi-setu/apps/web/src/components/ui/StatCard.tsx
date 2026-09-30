import React from 'react';

export interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  variant?: 'default' | 'danger' | 'warning' | 'success' | 'info';
  className?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtext,
  icon,
  trend,
  variant = 'default',
  className = '',
}) => {
  const variantBorder = {
    default: 'hover:border-slate-300',
    danger: 'border-l-4 border-l-red-600',
    warning: 'border-l-4 border-l-amber-500',
    success: 'border-l-4 border-l-emerald-600',
    info: 'border-l-4 border-l-blue-600',
  };

  const iconBg = {
    default: 'bg-slate-50 text-slate-700',
    danger: 'bg-red-50 text-red-600',
    warning: 'bg-amber-50 text-amber-700',
    success: 'bg-emerald-50 text-emerald-700',
    info: 'bg-blue-50 text-blue-700',
  };

  return (
    <div
      className={`
        bg-white rounded-xl border border-slate-200 p-4 sm:p-5 text-left shadow-[0_1px_3px_0_rgba(15,23,42,0.03)]
        hover:shadow-[0_4px_12px_0_rgba(15,23,42,0.05)] transition-all duration-200
        ${variantBorder[variant]}
        ${className}
      `}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
          {label}
        </span>
        {icon && (
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${iconBg[variant]}`}>
            {icon}
          </div>
        )}
      </div>

      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-xl sm:text-2xl font-bold font-mono text-slate-900 tracking-tight">
          {value}
        </span>
        {trend && (
          <span className={`text-[11px] font-semibold ${trend.isPositive ? 'text-emerald-700' : 'text-red-600'}`}>
            {trend.value}
          </span>
        )}
      </div>

      {subtext && (
        <p className="mt-1 text-[11px] text-slate-500 font-medium truncate">
          {subtext}
        </p>
      )}
    </div>
  );
};
