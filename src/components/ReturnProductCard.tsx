import React from 'react';
import { Pill, Trash2 } from 'lucide-react';
import { formatCurrency } from '@/utils';
import { RAZONES_DEVOLUCION } from '@/types';
import type { RazonDevolucion } from '@/types';

interface ReturnProductData {
  producto_id: string;
  producto_nombre: string;
  producto_codigo_sap: string;
  cantidad: number;
  lote: string;
  razon: RazonDevolucion | '';
  precio_unitario: number;
  max_cantidad: number;
}

interface ReturnProductCardProps {
  data: ReturnProductData;
  onChange: (data: Partial<ReturnProductData>) => void;
  onRemove: () => void;
}

export const ReturnProductCard: React.FC<ReturnProductCardProps> = ({
  data,
  onChange,
  onRemove,
}) => {
  const valorizado = data.cantidad * data.precio_unitario;

  return (
    <div className="p-4 border border-slate-300 rounded-lg">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-50 rounded-lg">
            <Pill className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">
              {data.producto_nombre}
            </p>
            <p className="text-xs text-slate-500">{data.producto_codigo_sap}</p>
          </div>
        </div>
        <button
          onClick={onRemove}
          className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded cursor-pointer transition-colors"
          aria-label="Eliminar producto"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div>
          <label
            htmlFor={`cantidad-${data.producto_id}`}
            className="block text-xs font-medium text-slate-600 mb-1"
          >
            Cantidad a devolver (max: {data.max_cantidad})
          </label>
          <input
            id={`cantidad-${data.producto_id}`}
            type="number"
            min={1}
            max={data.max_cantidad}
            value={data.cantidad}
            onChange={(e) =>
              onChange({
                cantidad: Math.min(
                  Math.max(1, Number(e.target.value)),
                  data.max_cantidad
                ),
              })
            }
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20"
          />
        </div>

        <div>
          <label
            htmlFor={`lote-${data.producto_id}`}
            className="block text-xs font-medium text-slate-600 mb-1"
          >
            Numero de Lote
          </label>
          <input
            id={`lote-${data.producto_id}`}
            type="text"
            value={data.lote}
            onChange={(e) => onChange({ lote: e.target.value })}
            placeholder="Ej: LOT-2025-001"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20"
          />
        </div>

        <div>
          <label
            htmlFor={`razon-${data.producto_id}`}
            className="block text-xs font-medium text-slate-600 mb-1"
          >
            Razon de devolucion
          </label>
          <select
            id={`razon-${data.producto_id}`}
            value={data.razon}
            onChange={(e) =>
              onChange({ razon: e.target.value as RazonDevolucion })
            }
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-700/20"
          >
            <option value="">Seleccionar...</option>
            {RAZONES_DEVOLUCION.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between">
        <span className="text-xs text-slate-500">
          Precio unitario: {formatCurrency(data.precio_unitario)}
        </span>
        <span className="text-sm font-semibold text-slate-900">
          Valorizado: {formatCurrency(valorizado)}
        </span>
      </div>
    </div>
  );
};

export type { ReturnProductData };
