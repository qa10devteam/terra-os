'use client';

import { useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

export interface ColumnDef<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  className?: string;
  hideOnMobile?: boolean;
}

interface DataTableProps<T extends { id: string }> {
  columns: ColumnDef<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  emptyState?: React.ReactNode;
}

export function DataTable<T extends { id: string }>({ columns, data, onRowClick, emptyState }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  function handleSort(key: string) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  }

  const sorted = [...data].sort((a, b) => {
    if (!sortKey) return 0;
    const av = (a as Record<string, unknown>)[sortKey];
    const bv = (b as Record<string, unknown>)[sortKey];
    if (av === null || av === undefined) return 1;
    if (bv === null || bv === undefined) return -1;
    const cmp = String(av).localeCompare(String(bv), 'pl', { numeric: true });
    return sortDir === 'asc' ? cmp : -cmp;
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-earth-800/60">
            {columns.map(col => (
              <th
                key={col.key}
                className={`px-3 py-2.5 text-left text-xs font-semibold text-earth-500 uppercase tracking-wide select-none ${col.sortable !== false ? 'cursor-pointer hover:text-earth-300' : ''} ${col.hideOnMobile ? 'hidden md:table-cell' : ''} ${col.className ?? ''}`}
                onClick={() => col.sortable !== false && handleSort(col.key)}
              >
                <div className="flex items-center gap-1">
                  {col.header}
                  {col.sortable !== false && sortKey === col.key && (
                    sortDir === 'asc' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-3 py-8 text-center">
                {emptyState ?? <span className="text-earth-600 text-sm">Brak danych</span>}
              </td>
            </tr>
          ) : sorted.map(row => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row)}
              className={`border-b border-earth-800/30 transition-colors ${onRowClick ? 'cursor-pointer hover:bg-earth-800/40' : ''}`}
            >
              {columns.map(col => (
                <td key={col.key} className={`px-3 py-2.5 ${col.hideOnMobile ? 'hidden md:table-cell' : ''} ${col.className ?? ''}`}>
                  {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
