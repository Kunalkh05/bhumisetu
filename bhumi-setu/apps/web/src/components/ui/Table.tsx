import React from 'react';

export const Table: React.FC<React.TableHTMLAttributes<HTMLTableElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <div className="w-full overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-2xs">
    <table className={`w-full text-left border-collapse text-xs sm:text-sm ${className}`} {...props}>
      {children}
    </table>
  </div>
);

export const TableHeader: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <thead className={`bg-slate-50/90 border-b border-slate-200 text-slate-700 select-none ${className}`} {...props}>
    {children}
  </thead>
);

export const TableBody: React.FC<React.HTMLAttributes<HTMLTableSectionElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <tbody className={`divide-y divide-slate-100 ${className}`} {...props}>
    {children}
  </tbody>
);

export const TableRow: React.FC<React.HTMLAttributes<HTMLTableRowElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <tr className={`hover:bg-slate-50/70 transition-colors duration-100 ${className}`} {...props}>
    {children}
  </tr>
);

export const TableHead: React.FC<React.ThHTMLAttributes<HTMLTableCellElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <th className={`px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-600 ${className}`} {...props}>
    {children}
  </th>
);

export const TableCell: React.FC<React.TdHTMLAttributes<HTMLTableCellElement>> = ({
  children,
  className = '',
  ...props
}) => (
  <td className={`px-4 py-3 text-slate-800 align-middle ${className}`} {...props}>
    {children}
  </td>
);

export const TableEmpty: React.FC<{ message?: string; colSpan?: number }> = ({
  message = 'No records found matching criteria.',
  colSpan = 5
}) => (
  <tr>
    <td colSpan={colSpan} className="px-4 py-8 text-center text-xs text-slate-400 font-medium">
      {message}
    </td>
  </tr>
);
