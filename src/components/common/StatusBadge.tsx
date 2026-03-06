import React from 'react';
import { cn } from '@/utils';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

interface StatusBadgeProps {
  label: string;
  variant?: BadgeVariant;
  withDot?: boolean;
  className?: string;
}

const variantStyles: Record<BadgeVariant, { bg: string; text: string; dot: string }> = {
  success: { bg: 'bg-green-50 border-green-200', text: 'text-green-700', dot: 'bg-green-500' },
  warning: { bg: 'bg-yellow-50 border-yellow-200', text: 'text-yellow-700', dot: 'bg-yellow-500' },
  danger: { bg: 'bg-red-50 border-red-200', text: 'text-red-700', dot: 'bg-red-500' },
  info: { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700', dot: 'bg-blue-500' },
  neutral: { bg: 'bg-slate-50 border-slate-200', text: 'text-slate-700', dot: 'bg-slate-500' },
};

const statusMap: Record<string, BadgeVariant> = {
  Aprobado: 'success',
  Aprobada: 'success',
  Enviado: 'warning',
  Pendiente: 'warning',
  'En Proceso': 'warning',
  Rechazado: 'danger',
  Rechazada: 'danger',
  Borrador: 'neutral',
  Calculada: 'info',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  variant,
  withDot = true,
  className,
}) => {
  const resolvedVariant = variant ?? statusMap[label] ?? 'neutral';
  const styles = variantStyles[resolvedVariant];

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border',
        styles.bg,
        styles.text,
        className
      )}
    >
      {withDot && (
        <span className={cn('w-1.5 h-1.5 rounded-full', styles.dot)} />
      )}
      {label}
    </span>
  );
};
