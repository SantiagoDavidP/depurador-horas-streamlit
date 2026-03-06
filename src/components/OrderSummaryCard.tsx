import React from 'react';
import { formatCurrency, formatDate } from '@/utils';
import { StatusBadge } from '@/components/common';
import type { Pedido } from '@/types';

interface OrderSummaryCardProps {
  pedido: Pedido;
  onViewDetail?: (pedido: Pedido) => void;
}

export const OrderSummaryCard: React.FC<OrderSummaryCardProps> = ({
  pedido,
  onViewDetail,
}) => {
  return (
    <div
      className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow cursor-pointer"
      onClick={() => onViewDetail?.(pedido)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onViewDetail?.(pedido);
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-900">
            {pedido.codigo_pedido}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {formatDate(pedido.fecha)}
          </p>
        </div>
        <StatusBadge label={pedido.estado} />
      </div>

      <div className="space-y-2 mb-3">
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Cliente</span>
          <span className="font-medium text-slate-900 text-right truncate ml-2">
            {pedido.cliente_razon_social}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">RUC</span>
          <span className="font-mono text-slate-700">{pedido.cliente_ruc}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-slate-500">Productos</span>
          <span className="text-slate-700">{pedido.detalles.length} items</span>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
        <span className="text-sm text-slate-500">Total</span>
        <span className="text-lg font-bold text-slate-900">
          {formatCurrency(pedido.total)}
        </span>
      </div>
    </div>
  );
};
