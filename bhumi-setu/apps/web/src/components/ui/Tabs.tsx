import React from 'react';

export interface TabItem<T extends string = string> {
  id: T;
  label: string;
  labelHi?: string;
  icon?: React.ReactNode;
  count?: number | string;
  badgeVariant?: 'neutral' | 'success' | 'warning' | 'danger' | 'info';
}

export interface TabsProps<T extends string = string> {
  tabs: TabItem<T>[];
  activeTab: T;
  onChange: (tabId: T) => void;
  variant?: 'pill' | 'underline';
  size?: 'sm' | 'md';
  language?: 'en' | 'hi';
  className?: string;
}

export function Tabs<T extends string = string>({
  tabs,
  activeTab,
  onChange,
  variant = 'pill',
  size = 'sm',
  language = 'en',
  className = '',
}: TabsProps<T>) {
  if (variant === 'underline') {
    return (
      <div className={`border-b border-slate-200 flex flex-wrap gap-6 text-xs sm:text-sm ${className}`} role="tablist">
        {tabs.map((tab) => {
          const isActive = tab.id === activeTab;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.id)}
              className={`
                pb-2.5 font-semibold transition-all duration-150 flex items-center gap-2 cursor-pointer border-b-2 -mb-[1px]
                ${isActive
                  ? 'border-[#0B3866] text-[#0B3866]'
                  : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                }
              `}
            >
              {tab.icon && <span className="flex-shrink-0">{tab.icon}</span>}
              <span>{language === 'hi' && tab.labelHi ? tab.labelHi : tab.label}</span>
              {tab.count !== undefined && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  isActive ? 'bg-[#0B3866]/10 text-[#0B3866]' : 'bg-slate-100 text-slate-600'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  // Pill variant (Segmented control)
  return (
    <div
      className={`inline-flex flex-wrap items-center p-1 bg-slate-100/90 rounded-lg border border-slate-200/80 gap-1 ${className}`}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        const sizeClasses = size === 'sm' ? 'px-2.5 py-1 text-xs' : 'px-3.5 py-1.5 text-xs sm:text-sm';

        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`
              rounded-md font-medium transition-all duration-150 flex items-center gap-1.5 cursor-pointer select-none
              ${sizeClasses}
              ${isActive
                ? 'bg-white text-slate-900 font-bold shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
              }
            `}
          >
            {tab.icon && <span className="flex-shrink-0">{tab.icon}</span>}
            <span>{language === 'hi' && tab.labelHi ? tab.labelHi : tab.label}</span>
            {tab.count !== undefined && (
              <span className={`px-1.5 py-0.2 rounded-md text-[10px] font-bold ${
                isActive ? 'bg-slate-100 text-slate-800' : 'bg-slate-200/70 text-slate-600'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
