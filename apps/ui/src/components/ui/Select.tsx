'use client';

import { useId } from 'react';
import { ChevronDown, AlertCircle } from 'lucide-react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value:        string;
  onChange:     (value: string) => void;
  options:      SelectOption[];
  placeholder?: string;
  disabled?:    boolean;
  label?:       string;
  error?:       string;
  className?:   string;
}

export function Select({
  value,
  onChange,
  options,
  placeholder,
  disabled  = false,
  label,
  error,
  className = '',
}: SelectProps) {
  const selectId = useId();

  const selectEl = (
    <div className="relative">
      <select
        id={selectId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={[
          'w-full px-3.5 py-2.5 pr-9 rounded-md',
          'appearance-none cursor-pointer',
          'bg-ink-800 border',
          'text-slate-100 text-sm',
          'focus:outline-none focus:ring-1',
          'transition-colors duration-150',
          'disabled:opacity-40 disabled:cursor-not-allowed',
          error
            ? 'border-nogo/50 focus:border-nogo/70 focus:ring-nogo/20'
            : 'border-ink-line focus:border-em/60 focus:ring-em/20',
          className,
        ]
          .filter(Boolean)
          .join(' ')}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-ink-900">
            {opt.label}
          </option>
        ))}
      </select>
      <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-500">
        <ChevronDown className="w-4 h-4" />
      </span>
    </div>
  );

  if (!label && !error) return selectEl;

  return (
    <div>
      {label && (
        <label htmlFor={selectId} className="block text-xs font-medium text-slate-400 mb-1.5">
          {label}
        </label>
      )}
      {selectEl}
      {error && (
        <p className="flex items-center gap-1 text-xs text-nogo mt-1">
          <AlertCircle className="w-3 h-3 shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}

export default Select;
