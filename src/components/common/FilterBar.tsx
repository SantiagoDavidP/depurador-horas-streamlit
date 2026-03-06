import React from 'react';
import { cn } from '@/utils';
import type { SelectOption } from '@/types';

interface FilterItem {
  key: string;
  label: string;
  options: SelectOption[];
  value: string;
}

interface FilterBarProps {
  filters: FilterItem[];
  onFilterChange: (key: string, value: string) => void;
  className?: string;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  filters,
  onFilterChange,
  className,
}) => {
  return (
    <div className={cn('flex flex-wrap items-center gap-3', className)}>
      {filters.map((filter) => (
        <select
          key={filter.key}
          value={filter.value}
          onChange={(e) => onFilterChange(filter.key, e.target.value)}
          className="px-3 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20 focus:border-blue-700 cursor-pointer transition-all bg-white"
          aria-label={filter.label}
        >
          {filter.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ))}
    </div>
  );
};
