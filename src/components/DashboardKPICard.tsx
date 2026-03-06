import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn, formatCurrency, formatNumber, formatPercentage } from '@/utils';

interface DashboardKPICardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  iconBgClass: string;
  isCurrency?: boolean;
  trending?: number;
  trendLabel?: string;
  subtitle?: string;
}

export const DashboardKPICard: React.FC<DashboardKPICardProps> = ({
  title,
  value,
  icon,
  iconBgClass,
  isCurrency = false,
  trending,
  trendLabel,
  subtitle,
}) => {
  const displayValue = isCurrency ? formatCurrency(value) : formatNumber(value);
  const isPositive = trending !== undefined && trending >= 0;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow cursor-pointer">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-slate-500">{title}</span>
        <div className={cn('p-2 rounded-lg', iconBgClass)}>{icon}</div>
      </div>
      <p className="text-3xl font-bold text-slate-900">{displayValue}</p>
      {trending !== undefined ? (
        <p
          className={cn(
            'text-xs mt-2 flex items-center gap-1',
            isPositive ? 'text-green-600' : 'text-red-600'
          )}
        >
          {isPositive ? (
            <TrendingUp className="w-3 h-3" />
          ) : (
            <TrendingDown className="w-3 h-3" />
          )}
          {formatPercentage(trending)} {trendLabel ?? 'vs mes anterior'}
        </p>
      ) : subtitle ? (
        <p className="text-xs text-slate-500 mt-2">{subtitle}</p>
      ) : null}
    </div>
  );
};
