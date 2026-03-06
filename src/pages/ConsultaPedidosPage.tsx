import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Download, Eye, FileDown, Edit } from 'lucide-react';
import { DataTable, Button, StatusBadge, SearchBar, Card, Modal } from '@/components/common';
import type { Column } from '@/components/common';
import { usePedidos } from '@/hooks';
import { formatCurrency, formatDate } from '@/utils';
import { pedidoService } from '@/services';
import { useNotificationStore } from '@/store';
import type { Pedido, SelectOption } from '@/types';

const ESTADO_OPTIONS: SelectOption[] = [
  { value: '', label: 'Todos los estados' },
  { value: 'Enviado', label: 'Enviado' },
  { value: 'Aprobado', label: 'Aprobado' },
  { value: 'Rechazado', label: 'Rechazado' },
  { value: 'Borrador', label: 'Borrador' },
];

const FECHA_OPTIONS: SelectOption[] = [
  { value: '', label: 'Todas las fechas' },
  { value: '1m', label: 'Ultimo mes' },
  { value: '3m', label: 'Ultimos 3 meses' },
  { value: '1y', label: 'Ultimo ano' },
];

export const ConsultaPedidosPage: React.FC = () => {
  const navigate = useNavigate();
  const addToast = useNotificationStore((s) => s.addToast);
  const [search, setSearch] = useState('');
  const [estadoFilter, setEstadoFilter] = useState('');
  const [fechaFilter, setFechaFilter] = useState('');
  const [selectedPedido, setSelectedPedido] = useState<Pedido | null>(null);

  const {
    pedidos,
    total,
    totalPages,
    isLoading,
    filters,
    setFilters,
  } = usePedidos({ page: 1, page_size: 10 });

  const handleSearch = useCallback(
    (value: string) => {
      setSearch(value);
      setFilters((prev) => ({ ...prev, search: value, page: 1 }));
    },
    [setFilters]
  );

  const handleEstadoChange = useCallback(
    (value: string) => {
      setEstadoFilter(value);
      setFilters((prev) => ({ ...prev, estado: value || undefined, page: 1 }));
    },
    [setFilters]
  );

  const handleFechaChange = useCallback(
    (value: string) => {
      setFechaFilter(value);
      setFilters((prev) => ({ ...prev, page: 1 }));
    },
    [setFilters]
  );

  const handleExportExcel = async () => {
    try {
      const blob = await pedidoService.exportExcel(filters);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'pedidos.xlsx';
      link.click();
      window.URL.revokeObjectURL(url);
      addToast({ type: 'success', title: 'Excel exportado' });
    } catch {
      addToast({ type: 'error', title: 'Error al exportar' });
    }
  };

  const handleDownloadPdf = async (pedidoId: string) => {
    try {
      const blob = await pedidoService.downloadPdf(pedidoId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `pedido_${pedidoId}.pdf`;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch {
      addToast({ type: 'error', title: 'Error al descargar PDF' });
    }
  };

  const columns: Column<Pedido>[] = [
    {
      key: 'codigo_pedido',
      header: 'Codigo',
      sortable: true,
      render: (p) => (
        <span className="font-mono text-xs font-semibold text-blue-700">
          {p.codigo_pedido}
        </span>
      ),
    },
    {
      key: 'cliente',
      header: 'Cliente',
      render: (p) => (
        <div>
          <p className="text-sm font-medium text-slate-900 truncate max-w-[200px]">
            {p.cliente_razon_social}
          </p>
          <p className="text-xs text-slate-500">RUC: {p.cliente_ruc}</p>
        </div>
      ),
    },
    {
      key: 'representante',
      header: 'Representante',
      render: (p) => <span className="text-sm text-slate-700">{p.representante}</span>,
    },
    {
      key: 'fecha',
      header: 'Fecha',
      sortable: true,
      render: (p) => <span className="text-sm text-slate-700">{formatDate(p.fecha)}</span>,
    },
    {
      key: 'total',
      header: 'Total',
      sortable: true,
      align: 'right',
      render: (p) => (
        <span className="text-sm font-semibold text-slate-900">
          {formatCurrency(p.total)}
        </span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (p) => <StatusBadge label={p.estado} />,
    },
    {
      key: 'acciones',
      header: 'Acciones',
      align: 'center',
      render: (p) => (
        <div className="flex items-center justify-center gap-1">
          <button
            onClick={() => setSelectedPedido(p)}
            className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded cursor-pointer transition-colors"
            aria-label="Ver detalle"
          >
            <Eye className="w-4 h-4" />
          </button>
          <button
            onClick={() => handleDownloadPdf(p.id)}
            className="p-1.5 text-slate-400 hover:text-green-600 hover:bg-green-50 rounded cursor-pointer transition-colors"
            aria-label="Descargar PDF"
          >
            <FileDown className="w-4 h-4" />
          </button>
          {p.estado === 'Enviado' && (
            <button
              onClick={() => navigate(`/pedidos/editar/${p.id}`)}
              className="p-1.5 text-slate-400 hover:text-yellow-600 hover:bg-yellow-50 rounded cursor-pointer transition-colors"
              aria-label="Editar"
            >
              <Edit className="w-4 h-4" />
            </button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <div className="flex flex-col md:flex-row items-start md:items-center gap-3">
          <SearchBar
            value={search}
            onChange={handleSearch}
            placeholder="Buscar por codigo o cliente..."
            className="flex-1 min-w-[200px]"
          />
          <select
            value={estadoFilter}
            onChange={(e) => handleEstadoChange(e.target.value)}
            className="px-3 py-2.5 border border-slate-300 rounded-lg text-sm cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-700/20"
            aria-label="Filtrar por estado"
          >
            {ESTADO_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <select
            value={fechaFilter}
            onChange={(e) => handleFechaChange(e.target.value)}
            className="px-3 py-2.5 border border-slate-300 rounded-lg text-sm cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-700/20"
            aria-label="Filtrar por fecha"
          >
            {FECHA_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <div className="flex gap-2 ml-auto">
            <Button
              variant="outline"
              leftIcon={<Download className="w-4 h-4" />}
              onClick={handleExportExcel}
            >
              Exportar
            </Button>
            <Button
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => navigate('/pedidos/nuevo')}
            >
              Nuevo Pedido
            </Button>
          </div>
        </div>
      </Card>

      {/* Table */}
      <DataTable
        columns={columns}
        data={pedidos}
        keyExtractor={(p) => p.id}
        isLoading={isLoading}
        emptyMessage="No se encontraron pedidos"
        currentPage={filters.page ?? 1}
        totalPages={totalPages}
        total={total}
        pageSize={filters.page_size ?? 10}
        onPageChange={(page) => setFilters((prev) => ({ ...prev, page }))}
        onPageSizeChange={(size) =>
          setFilters((prev) => ({ ...prev, page_size: size, page: 1 }))
        }
        onSort={(key, direction) =>
          setFilters((prev) => ({
            ...prev,
            sort_by: key,
            sort_direction: direction,
          }))
        }
      />

      {/* Detail Modal */}
      {selectedPedido && (
        <Modal
          isOpen={Boolean(selectedPedido)}
          onClose={() => setSelectedPedido(null)}
          title={`Pedido ${selectedPedido.codigo_pedido}`}
          size="lg"
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
              <div>
                <p className="text-xs text-slate-500">Cliente</p>
                <p className="text-sm font-medium text-slate-900">
                  {selectedPedido.cliente_razon_social}
                </p>
                <p className="text-xs text-slate-600">
                  RUC: {selectedPedido.cliente_ruc}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Representante</p>
                <p className="text-sm font-medium text-slate-900">
                  {selectedPedido.representante}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Condicion de Pago</p>
                <p className="text-sm font-medium text-slate-900">
                  {selectedPedido.condicion_pago}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Fecha</p>
                <p className="text-sm font-medium text-slate-900">
                  {formatDate(selectedPedido.fecha)}
                </p>
              </div>
            </div>

            <div>
              <p className="text-sm font-medium text-slate-700 mb-2">
                Productos ({selectedPedido.detalles.length})
              </p>
              <div className="space-y-2">
                {selectedPedido.detalles.map((det) => (
                  <div
                    key={det.id}
                    className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
                  >
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {det.producto_nombre}
                      </p>
                      <p className="text-xs text-slate-500">
                        {det.producto_codigo_sap} - {det.tipo}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-slate-900">
                        {det.cantidad} unid.
                      </p>
                      <p className="text-xs text-slate-500">
                        {formatCurrency(det.subtotal)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-200 flex items-center justify-between">
              <StatusBadge label={selectedPedido.estado} />
              <span className="text-lg font-bold text-slate-900">
                Total: {formatCurrency(selectedPedido.total)}
              </span>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
