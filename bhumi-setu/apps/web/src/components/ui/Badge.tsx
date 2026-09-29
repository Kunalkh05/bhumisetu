import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'accent';
  size?: 'sm' | 'md';
  icon?: React.ReactNode;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'sm',
  icon,
  dot = false,
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center font-medium tracking-tight border transition-colors select-none';

  const sizeStyles = {
    sm: 'text-[10px] px-2 py-0.5 rounded-md gap-1 font-semibold uppercase tracking-wider',
    md: 'text-xs px-2.5 py-1 rounded-md gap-1.5 font-medium',
  };

  const variantStyles = {
    neutral: 'bg-slate-50 text-slate-700 border-slate-200',
    success: 'bg-emerald-50 text-emerald-800 border-emerald-200',
    warning: 'bg-amber-50 text-amber-800 border-amber-200',
    danger: 'bg-red-50 text-red-800 border-red-200',
    info: 'bg-blue-50 text-blue-800 border-blue-200',
    accent: 'bg-orange-50 text-orange-900 border-orange-200',
  };

  const dotColors = {
    neutral: 'bg-slate-400',
    success: 'bg-emerald-600',
    warning: 'bg-amber-600',
    danger: 'bg-red-600',
    info: 'bg-blue-600',
    accent: 'bg-orange-600',
  };

  return (
    <span
      className={`
        ${baseStyles}
        ${sizeStyles[size]}
        ${variantStyles[variant]}
        ${className}
      `}
      {...props}
    >
      {dot && (
        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotColors[variant]}`} />
      )}
      {icon && (
        <span className="flex-shrink-0">{icon}</span>
      )}
      <span>{children}</span>
    </span>
  );
};
