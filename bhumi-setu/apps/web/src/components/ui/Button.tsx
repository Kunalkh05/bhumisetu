import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'danger' | 'ghost' | 'success';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  className = '',
  disabled,
  ...props
}, ref) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-150 select-none cursor-pointer focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0B3866] disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none';

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 rounded-md gap-1.5',
    md: 'text-xs sm:text-sm px-3.5 py-2 rounded-lg gap-2',
    lg: 'text-sm sm:text-base px-5 py-2.5 rounded-lg gap-2.5 font-semibold',
  };

  const variantStyles = {
    primary: 'bg-[#0B3866] hover:bg-[#072442] active:bg-[#051a30] text-white shadow-xs border border-transparent',
    secondary: 'bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-800 border border-slate-200 shadow-xs hover:border-slate-300',
    accent: 'bg-[#F37021] hover:bg-[#D95A10] active:bg-[#BF4D0C] text-white shadow-xs border border-transparent font-semibold',
    danger: 'bg-red-600 hover:bg-red-700 active:bg-red-800 text-white shadow-xs border border-transparent',
    success: 'bg-emerald-700 hover:bg-emerald-800 active:bg-emerald-900 text-white shadow-xs border border-transparent',
    ghost: 'bg-transparent hover:bg-slate-100 active:bg-slate-200 text-slate-700 border border-transparent',
  };

  return (
    <button
      ref={ref}
      disabled={disabled || isLoading}
      className={`
        ${baseStyles}
        ${sizeStyles[size]}
        ${variantStyles[variant]}
        ${fullWidth ? 'w-full' : ''}
        ${className}
      `}
      {...props}
    >
      {isLoading ? (
        <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin flex-shrink-0" />
      ) : leftIcon ? (
        <span className="flex-shrink-0">{leftIcon}</span>
      ) : null}
      
      {children}
      
      {!isLoading && rightIcon && (
        <span className="flex-shrink-0">{rightIcon}</span>
      )}
    </button>
  );
});

Button.displayName = 'Button';
