import React, { useState, useCallback } from 'react';
import { Clock } from 'lucide-react';
import { SearchBar, Card } from '@/components/common';
import { OrderApprovalCard } from '@/components';
import { usePedidosPendientes, usePedidos } from '@/hooks';
import type { SelectOption } from '@/types';

const SORT_OPTIONS: SelectOption[] = [
  { value: 'recent', label: 'Mas recientes' },
  { value: 'amount', label: 'Monto mayor' },
  { value: 'oldest', label: 'Fecha mas antigua' },
];

const SELLER_OPTIONS: SelectOption[] = [
  { value: '', label: 'Todos los vendedores' },
];

export const AprobacionPedidosPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('recent');
  const [vendedorFilter, setVendedorFilter] = useState('');

  const { pedidos, total, isLoading, error, refetch } = usePedidosPendientes({
    search: search || undefined,
    sort_by: sortBy,
    page: 1,
    page_size: 50,
  });

  const { approvePedido, rejectPedido } = usePedidos();

  const handleApprove = useCallback(
    async (id: string) => {
      await approvePedido(id);
      refetch();
    },
    [approvePedido, refetch]
  );

  const handleReject = useCallback(
    async (id: string, motivo: string) => {
      await rejectPedido(id, motivo);
      refetch();
    },
    [rejectPedido, refetch]
  );

  const handleSearch = useCallback((value: string) => {
    setSearch(value);
  }, []);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-16 bg-slate-200 rounded-xl animate-pulse" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-48 bg-slate-200 rounded-xl animate-pulse" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <p className="text-sm text-red-600 mb-4">{error}</p>
        <button
          onClick={refetch}
          className="px-4 py-2 text-sm font-medium text-blue-700 border border-blue-700 rounded-lg hover:bg-blue-50 cursor-pointer transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <SearchBar
            value={search}
            onChange={handleSearch}
            placeholder="Buscar por codigo o cliente..."
            className="flex-1 min-w-[200px]"
          />
          <select
            value={vendedorFilter}
            onChange={(e) => setVendedorFilter(e.target.value)}
            className="px-3 py-2.5 border border-slate-300 rounded-lg text-sm cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-700/20"
            aria-label="Filtrar por vendedor"
          >
            {SELLER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-2.5 border border-slate-300 rounded-lg text-sm cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-700/20"
            aria-label="Ordenar por"
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                Ordenar: {o.label}
              </option>
            ))}
          </select>
          <div className="flex items-center gap-2 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded-lg ml-auto">
            <Clock className="w-4 h-4 text-yellow-600" />
            <span className="text-sm font-medium text-yellow-900">
              {total} pendientes
            </span>
          </div>
        </div>
      </Card>

      {/* Order Cards */}
      {pedidos.length === 0 ? (
        <div className="text-center py-16">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-50 rounded-full mb-4">
            <Clock className="w-8 h-8 text-green-600" />
          </div>
          <h3 className="text-lg font-semibold text-slate-900 mb-2">
            Sin pedidos pendientes
          </h3>
          <p className="text-sm text-slate-500">
            Todos los pedidos han sido procesados
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {pedidos.map((pedido) => (
            <OrderApprovalCard
              key={pedido.id}
              pedido={pedido}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>
      )}
    </div>
  );
};
