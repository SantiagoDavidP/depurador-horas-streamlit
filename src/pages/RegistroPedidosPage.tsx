import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Building2,
  Package,
  Plus,
  Trash2,
  Save,
  Send,
  Info,
} from 'lucide-react';
import {
  Card,
  CardHeader,
  Button,
  FormField,
  Input,
  SelectField,
} from '@/components/common';
import { ProductSearchModal } from '@/components';
import { usePedidos } from '@/hooks';
import { useNotificationStore } from '@/store';
import { formatCurrency, cn } from '@/utils';
import type { Producto, TipoDetalle } from '@/types';
import { CONDICIONES_PAGO } from '@/types';

const clienteSchema = z.object({
  cliente_ruc: z
    .string()
    .length(11, 'El RUC debe tener 11 digitos')
    .regex(/^\d+$/, 'Solo numeros'),
  representante: z.string().min(1, 'El representante es obligatorio'),
  condicion_pago: z.string().min(1, 'Seleccione condicion de pago'),
});

type ClienteFormData = z.infer<typeof clienteSchema>;

interface LineaPedido {
  producto: Producto;
  cantidad: number;
  tipo: TipoDetalle;
}

export const RegistroPedidosPage: React.FC = () => {
  const navigate = useNavigate();
  const { createPedido } = usePedidos();
  const addToast = useNotificationStore((s) => s.addToast);
  const [lineas, setLineas] = useState<LineaPedido[]>([]);
  const [showProductModal, setShowProductModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [razonSocial, setRazonSocial] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors },
    getValues,
  } = useForm<ClienteFormData>({
    resolver: zodResolver(clienteSchema),
  });

  const handleAddProduct = (
    producto: Producto,
    cantidad: number,
    tipo: TipoDetalle
  ) => {
    setLineas((prev) => [...prev, { producto, cantidad, tipo }]);
  };

  const handleRemoveLine = (index: number) => {
    setLineas((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCantidadChange = (index: number, value: number) => {
    setLineas((prev) =>
      prev.map((l, i) =>
        i === index ? { ...l, cantidad: Math.max(1, value) } : l
      )
    );
  };

  const { subtotal, igv, total, totalBonificaciones } = useMemo(() => {
    const sub = lineas.reduce((acc, l) => {
      if (l.tipo === 'Venta') {
        return acc + l.cantidad * l.producto.precio_vvf;
      }
      return acc;
    }, 0);
    const tax = sub * 0.18;
    const bonif = lineas
      .filter((l) => l.tipo === 'Bonificacion')
      .reduce((acc, l) => acc + l.cantidad, 0);
    return {
      subtotal: sub,
      igv: tax,
      total: sub + tax,
      totalBonificaciones: bonif,
    };
  }, [lineas]);

  const onSubmit = async (data: ClienteFormData) => {
    if (lineas.length === 0) {
      addToast({
        type: 'warning',
        title: 'Sin productos',
        message: 'Agregue al menos un producto al pedido',
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await createPedido({
        cliente_ruc: data.cliente_ruc,
        representante: data.representante,
        condicion_pago: data.condicion_pago,
        detalles: lineas.map((l) => ({
          producto_id: l.producto.id,
          cantidad: l.cantidad,
          tipo: l.tipo,
        })),
      });
      if (result) {
        navigate('/pedidos');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSearchRuc = async () => {
    const ruc = getValues('cliente_ruc');
    if (ruc.length === 11) {
      setRazonSocial('Cargando...');
      try {
        const res = await fetch(`http://localhost:8000/api/clientes/${ruc}`);
        if (res.ok) {
          const client = await res.json();
          setRazonSocial(client.razon_social ?? '');
        } else {
          setRazonSocial('No encontrado');
        }
      } catch {
        setRazonSocial('Error al buscar');
      }
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Alert */}
      <div className="flex items-start gap-3 bg-blue-50 border border-blue-200 rounded-xl p-4">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-blue-900">
            Instrucciones para registro de pedidos
          </p>
          <p className="text-xs text-blue-700 mt-1">
            Complete la informacion del cliente, seleccione productos y
            bonificaciones. El sistema calculara automaticamente el total segun
            los minimos del distribuidor.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        {/* Client Info */}
        <Card className="mb-6">
          <CardHeader
            title="Informacion del Cliente"
            icon={<Building2 className="w-5 h-5 text-blue-700" />}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField
              label="RUC del Cliente"
              htmlFor="cliente_ruc"
              required
              error={errors.cliente_ruc?.message}
            >
              <Input
                id="cliente_ruc"
                placeholder="20123456789"
                maxLength={11}
                hasError={Boolean(errors.cliente_ruc)}
                {...register('cliente_ruc')}
                rightAction={
                  <button
                    type="button"
                    onClick={handleSearchRuc}
                    className="p-1.5 text-blue-700 hover:bg-blue-50 rounded cursor-pointer transition-colors"
                    aria-label="Buscar RUC"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
                      />
                    </svg>
                  </button>
                }
              />
            </FormField>

            <FormField label="Razon Social" htmlFor="razon_social">
              <Input
                id="razon_social"
                value={razonSocial}
                readOnly
                className="bg-slate-50"
              />
            </FormField>

            <FormField
              label="Representante"
              htmlFor="representante"
              required
              error={errors.representante?.message}
            >
              <Input
                id="representante"
                placeholder="Nombre del contacto"
                hasError={Boolean(errors.representante)}
                {...register('representante')}
              />
            </FormField>

            <FormField
              label="Condicion de Pago"
              htmlFor="condicion_pago"
              required
              error={errors.condicion_pago?.message}
            >
              <SelectField
                id="condicion_pago"
                placeholder="Seleccionar..."
                options={CONDICIONES_PAGO}
                hasError={Boolean(errors.condicion_pago)}
                {...register('condicion_pago')}
              />
            </FormField>
          </div>
        </Card>

        {/* Products */}
        <Card className="mb-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
              <Package className="w-5 h-5 text-blue-700" />
              Productos del Pedido
            </h2>
            <Button
              type="button"
              leftIcon={<Plus className="w-4 h-4" />}
              onClick={() => setShowProductModal(true)}
            >
              Agregar Producto
            </Button>
          </div>

          {lineas.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-sm border border-dashed border-slate-300 rounded-lg">
              Aun no hay productos. Use el boton "Agregar Producto" para
              comenzar.
            </div>
          ) : (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50">
                      <th className="text-left px-4 py-3 font-medium text-slate-500">
                        Codigo SAP
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-slate-500">
                        Producto
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-slate-500">
                        Tipo
                      </th>
                      <th className="text-right px-4 py-3 font-medium text-slate-500">
                        Cantidad
                      </th>
                      <th className="text-right px-4 py-3 font-medium text-slate-500">
                        Precio Unit.
                      </th>
                      <th className="text-right px-4 py-3 font-medium text-slate-500">
                        Subtotal
                      </th>
                      <th className="text-center px-4 py-3 font-medium text-slate-500">
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {lineas.map((linea, idx) => {
                      const precio =
                        linea.tipo === 'Bonificacion'
                          ? 0
                          : linea.producto.precio_vvf;
                      const lineSubtotal = linea.cantidad * precio;

                      return (
                        <tr
                          key={`${linea.producto.id}-${idx}`}
                          className="hover:bg-slate-50 transition-colors"
                        >
                          <td className="px-4 py-3 font-mono text-xs text-slate-600">
                            {linea.producto.codigo_sap}
                          </td>
                          <td className="px-4 py-3">
                            <p className="font-medium text-slate-900">
                              {linea.producto.nombre}
                            </p>
                            <p className="text-xs text-slate-500">
                              {linea.producto.molecula}
                            </p>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={cn(
                                'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                                linea.tipo === 'Bonificacion'
                                  ? 'bg-green-50 text-green-700'
                                  : 'bg-blue-50 text-blue-700'
                              )}
                            >
                              {linea.tipo}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <input
                              type="number"
                              min={1}
                              value={linea.cantidad}
                              onChange={(e) =>
                                handleCantidadChange(
                                  idx,
                                  Number(e.target.value)
                                )
                              }
                              className="w-20 px-2 py-1 border border-slate-300 rounded text-sm text-right focus:outline-none focus:ring-1 focus:ring-blue-700/20"
                            />
                          </td>
                          <td
                            className={cn(
                              'px-4 py-3 text-right font-medium',
                              linea.tipo === 'Bonificacion'
                                ? 'text-slate-500'
                                : 'text-slate-900'
                            )}
                          >
                            {formatCurrency(precio)}
                          </td>
                          <td
                            className={cn(
                              'px-4 py-3 text-right font-semibold',
                              linea.tipo === 'Bonificacion'
                                ? 'text-slate-500'
                                : 'text-slate-900'
                            )}
                          >
                            {formatCurrency(lineSubtotal)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <button
                              type="button"
                              onClick={() => handleRemoveLine(idx)}
                              className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer transition-colors"
                              aria-label="Eliminar producto"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </Card>

        {/* Totals */}
        {lineas.length > 0 && (
          <Card className="mb-6">
            <div className="flex flex-col items-end space-y-2">
              <div className="flex justify-between w-full max-w-xs text-sm">
                <span className="text-slate-500">Subtotal:</span>
                <span className="font-medium text-slate-900">
                  {formatCurrency(subtotal)}
                </span>
              </div>
              <div className="flex justify-between w-full max-w-xs text-sm">
                <span className="text-slate-500">IGV (18%):</span>
                <span className="font-medium text-slate-900">
                  {formatCurrency(igv)}
                </span>
              </div>
              {totalBonificaciones > 0 && (
                <div className="flex justify-between w-full max-w-xs text-sm">
                  <span className="text-slate-500">Bonificaciones:</span>
                  <span className="font-medium text-green-600">
                    {totalBonificaciones} unid.
                  </span>
                </div>
              )}
              <div className="flex justify-between w-full max-w-xs text-base border-t border-slate-200 pt-2 mt-2">
                <span className="font-semibold text-slate-900">Total:</span>
                <span className="font-bold text-slate-900">
                  {formatCurrency(total)}
                </span>
              </div>
            </div>
          </Card>
        )}

        {/* Actions */}
        <div className="flex flex-col sm:flex-row justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            leftIcon={<Save className="w-4 h-4" />}
          >
            Guardar Borrador
          </Button>
          <Button
            type="submit"
            isLoading={isSubmitting}
            leftIcon={<Send className="w-4 h-4" />}
          >
            Enviar Pedido
          </Button>
        </div>
      </form>

      <ProductSearchModal
        isOpen={showProductModal}
        onClose={() => setShowProductModal(false)}
        onSelect={handleAddProduct}
      />
    </div>
  );
};
