import React, { useState, useMemo } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { PackageX, Plus, Send, Search } from 'lucide-react';
import {
  Card,
  Button,
  FormField,
  Input,
  StatusBadge,
  DataTable,
} from '@/components/common';
import type { Column } from '@/components/common';
import { ReturnProductCard } from '@/components';
import type { ReturnProductData } from '@/components';
import { useDevoluciones } from '@/hooks';
import { pedidoService } from '@/services';
import { useNotificationStore } from '@/store';
import { formatCurrency, formatDate } from '@/utils';
import type { Devolucion, Pedido, RazonDevolucion } from '@/types';

const devolucionSchema = z.object({
  pedido_codigo: z.string().min(1, 'El codigo de pedido es obligatorio'),
  numero_factura: z
    .string()
    .regex(/^F\d{3}-\d{8}$/, 'Formato invalido. Use: F001-00012345'),
  observaciones: z.string().optional(),
});

type DevolucionFormData = z.infer<typeof devolucionSchema>;

export const GestionDevolucionesPage: React.FC = () => {
  const addToast = useNotificationStore((s) => s.addToast);
  const [activeTab, setActiveTab] = useState<'registrar' | 'historial'>(
    'registrar'
  );
  const [pedidoInfo, setPedidoInfo] = useState<Pedido | null>(null);
  const [productos, setProductos] = useState<ReturnProductData[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { devoluciones, total, totalPages, isLoading, filters, setFilters, createDevolucion } =
    useDevoluciones();

  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
    reset,
  } = useForm<DevolucionFormData>({
    resolver: zodResolver(devolucionSchema),
  });

  const handleSearchPedido = async () => {
    const codigo = getValues('pedido_codigo');
    if (!codigo) return;
    setIsSearching(true);
    try {
      const res = await pedidoService.list({ search: codigo, page: 1, page_size: 1 });
      if (res.items.length > 0) {
        const p = res.items[0];
        setPedidoInfo(p);
        setProductos([]);
      } else {
        addToast({ type: 'warning', title: 'Pedido no encontrado' });
        setPedidoInfo(null);
      }
    } catch {
      addToast({ type: 'error', title: 'Error al buscar pedido' });
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddProducto = () => {
    if (!pedidoInfo) return;
    const availableDetalles = pedidoInfo.detalles.filter(
      (d) =>
        d.tipo === 'Venta' &&
        !productos.some((p) => p.producto_id === d.producto_id)
    );
    if (availableDetalles.length === 0) {
      addToast({
        type: 'info',
        title: 'Sin productos disponibles',
        message: 'Todos los productos ya fueron agregados',
      });
      return;
    }
    const det = availableDetalles[0];
    setProductos((prev) => [
      ...prev,
      {
        producto_id: det.producto_id,
        producto_nombre: det.producto_nombre,
        producto_codigo_sap: det.producto_codigo_sap,
        cantidad: 1,
        lote: '',
        razon: '' as RazonDevolucion,
        precio_unitario: det.precio_unitario,
        max_cantidad: det.cantidad,
      },
    ]);
  };

  const handleUpdateProducto = (
    index: number,
    data: Partial<ReturnProductData>
  ) => {
    setProductos((prev) =>
      prev.map((p, i) => (i === index ? { ...p, ...data } : p))
    );
  };

  const handleRemoveProducto = (index: number) => {
    setProductos((prev) => prev.filter((_, i) => i !== index));
  };

  const resumen = useMemo(() => {
    const totalItems = productos.length;
    const totalUnidades = productos.reduce((a, p) => a + p.cantidad, 0);
    const totalValorizado = productos.reduce(
      (a, p) => a + p.cantidad * p.precio_unitario,
      0
    );
    return { totalItems, totalUnidades, totalValorizado };
  }, [productos]);

  const onSubmit = async (data: DevolucionFormData) => {
    if (!pedidoInfo) return;
    if (productos.length === 0) {
      addToast({
        type: 'warning',
        title: 'Sin productos',
        message: 'Agregue al menos un producto para devolver',
      });
      return;
    }

    const invalid = productos.some(
      (p) => !p.razon || !p.lote || p.cantidad < 1
    );
    if (invalid) {
      addToast({
        type: 'warning',
        title: 'Datos incompletos',
        message: 'Complete todos los campos de cada producto',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      await createDevolucion({
        pedido_id: pedidoInfo.id,
        numero_factura: data.numero_factura,
        productos: productos.map((p) => ({
          producto_id: p.producto_id,
          cantidad: p.cantidad,
          lote: p.lote,
          razon: p.razon as RazonDevolucion,
        })),
        observaciones: data.observaciones,
      });
      reset();
      setPedidoInfo(null);
      setProductos([]);
    } finally {
      setIsSubmitting(false);
    }
  };

  const historialColumns: Column<Devolucion>[] = [
    {
      key: 'codigo',
      header: 'Codigo',
      render: (d) => (
        <span className="font-mono text-xs font-semibold text-blue-700">
          {d.codigo_devolucion}
        </span>
      ),
    },
    {
      key: 'pedido',
      header: 'Pedido',
      render: (d) => (
        <span className="text-sm text-slate-700">{d.pedido_codigo}</span>
      ),
    },
    {
      key: 'cliente',
      header: 'Cliente',
      render: (d) => (
        <div>
          <p className="text-sm text-slate-900">{d.cliente_razon_social}</p>
          <p className="text-xs text-slate-500">RUC: {d.cliente_ruc}</p>
        </div>
      ),
    },
    {
      key: 'producto',
      header: 'Producto',
      render: (d) => (
        <span className="text-sm text-slate-700">{d.producto_nombre}</span>
      ),
    },
    {
      key: 'cantidad',
      header: 'Cant.',
      align: 'right',
      render: (d) => (
        <span className="text-sm text-slate-900">{d.cantidad}</span>
      ),
    },
    {
      key: 'valorizado',
      header: 'Valorizado',
      align: 'right',
      render: (d) => (
        <span className="text-sm font-medium text-slate-900">
          {formatCurrency(d.valorizado)}
        </span>
      ),
    },
    {
      key: 'estado',
      header: 'Estado',
      render: (d) => <StatusBadge label={d.estado} />,
    },
  ];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200">
        <button
          className={`px-4 py-3 text-sm font-medium cursor-pointer transition-colors ${
            activeTab === 'registrar'
              ? 'text-blue-700 border-b-2 border-blue-700'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('registrar')}
        >
          Registrar Devolucion
        </button>
        <button
          className={`px-4 py-3 text-sm font-medium cursor-pointer transition-colors ${
            activeTab === 'historial'
              ? 'text-blue-700 border-b-2 border-blue-700'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          onClick={() => setActiveTab('historial')}
        >
          Historial
        </button>
      </div>

      {activeTab === 'registrar' ? (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Pedido & Factura */}
          <Card>
            <h2 className="text-base font-semibold text-slate-900 mb-5 flex items-center gap-2">
              <PackageX className="w-5 h-5 text-red-600" />
              Informacion de la Devolucion
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <FormField
                label="Pedido Asociado"
                htmlFor="pedido_codigo"
                required
                error={errors.pedido_codigo?.message}
              >
                <Input
                  id="pedido_codigo"
                  placeholder="PED-2025-XXXX"
                  {...register('pedido_codigo')}
                  hasError={Boolean(errors.pedido_codigo)}
                  rightAction={
                    <button
                      type="button"
                      onClick={handleSearchPedido}
                      disabled={isSearching}
                      className="p-1.5 text-blue-700 hover:bg-blue-50 rounded cursor-pointer transition-colors"
                      aria-label="Buscar pedido"
                    >
                      <Search className="w-4 h-4" />
                    </button>
                  }
                />
              </FormField>
              <FormField
                label="Numero de Factura"
                htmlFor="numero_factura"
                required
                error={errors.numero_factura?.message}
              >
                <Input
                  id="numero_factura"
                  placeholder="F001-00012345"
                  {...register('numero_factura')}
                  hasError={Boolean(errors.numero_factura)}
                />
              </FormField>
            </div>

            {/* Auto-filled client info */}
            {pedidoInfo && (
              <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
                <p className="text-xs font-medium text-slate-500 mb-2">
                  Cliente del Pedido
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {pedidoInfo.cliente_razon_social}
                    </p>
                    <p className="text-xs text-slate-600">
                      RUC: {pedidoInfo.cliente_ruc}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Representante</p>
                    <p className="text-sm text-slate-900">
                      {pedidoInfo.representante}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Fecha Pedido</p>
                    <p className="text-sm text-slate-900">
                      {formatDate(pedidoInfo.fecha)}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </Card>

          {/* Products to return */}
          {pedidoInfo && (
            <Card>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-semibold text-slate-900">
                  Productos a Devolver
                </h3>
                <Button
                  type="button"
                  size="sm"
                  leftIcon={<Plus className="w-4 h-4" />}
                  onClick={handleAddProducto}
                >
                  Agregar Producto
                </Button>
              </div>

              {productos.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm border border-dashed border-slate-300 rounded-lg">
                  Use el boton "Agregar Producto" para seleccionar items a
                  devolver
                </div>
              ) : (
                <div className="space-y-3">
                  {productos.map((prod, idx) => (
                    <ReturnProductCard
                      key={`${prod.producto_id}-${idx}`}
                      data={prod}
                      onChange={(data) => handleUpdateProducto(idx, data)}
                      onRemove={() => handleRemoveProducto(idx)}
                    />
                  ))}
                </div>
              )}
            </Card>
          )}

          {/* Observaciones */}
          {pedidoInfo && (
            <Card>
              <FormField
                label="Observaciones adicionales"
                htmlFor="observaciones"
              >
                <textarea
                  id="observaciones"
                  {...register('observaciones')}
                  rows={3}
                  placeholder="Detalles complementarios sobre la devolucion..."
                  className="w-full px-3 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20 focus:border-blue-700 resize-none"
                />
              </FormField>
            </Card>
          )}

          {/* Summary & Submit */}
          {productos.length > 0 && (
            <Card>
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="space-y-1">
                  <p className="text-sm text-slate-500">
                    Total productos: {resumen.totalItems} items ({resumen.totalUnidades}{' '}
                    unidades)
                  </p>
                  <p className="text-lg font-bold text-slate-900">
                    Valorizado total: {formatCurrency(resumen.totalValorizado)}
                  </p>
                </div>
                <Button
                  type="submit"
                  isLoading={isSubmitting}
                  leftIcon={<Send className="w-4 h-4" />}
                >
                  Registrar Devolucion
                </Button>
              </div>
            </Card>
          )}
        </form>
      ) : (
        /* Historial Tab */
        <DataTable
          columns={historialColumns}
          data={devoluciones}
          keyExtractor={(d) => d.id}
          isLoading={isLoading}
          emptyMessage="No hay devoluciones registradas"
          currentPage={filters.page ?? 1}
          totalPages={totalPages}
          total={total}
          pageSize={filters.page_size ?? 10}
          onPageChange={(page) => setFilters((prev) => ({ ...prev, page }))}
          onPageSizeChange={(size) =>
            setFilters((prev) => ({ ...prev, page_size: size, page: 1 }))
          }
        />
      )}
    </div>
  );
};
