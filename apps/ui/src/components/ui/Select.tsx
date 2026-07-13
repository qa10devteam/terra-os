'use client';

import { useId } from 'react';
import { ChevronDown, AlertCircle } from 'lucide-react';

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  label?: string;
  error?: string;
}

export function Select({
  value,
  onChange,
  options,
  placeholder,
  disabled = false,
  label,
  error,
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
          'input-base appearance-none w-full pr-8 cursor-pointer',
          error
            ? 'border-accent-danger/50 focus:border-accent-danger/70 focus:ring-accent-danger/20'
            : '',
          disabled ? 'opacity-50 cursor-not-allowed' : '',
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
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {/* Chevron icon — pointer-events-none so select is still clickable */}
      <span className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-earth-500">
        <ChevronDown className="w-4 h-4" />
      </span>
    </div>
  );

  if (!label && !error) return selectEl;

  return (
    <div>
      {label && (
        <label
          htmlFor={selectId}
          className="label-base block mb-1.5"
        >
          {label}
        </label>
      )}
      {selectEl}
      {error && (
        <p className="flex items-center gap-1 text-xs text-accent-danger mt-1">
          <AlertCircle className="w-3 h-3 shrink-0" />
          {error}
        </p>
      )}
    </div>
  );
}

export default Select;
