import React, { useState, useEffect, useCallback } from 'react';
import { Search, Plus, Pill } from 'lucide-react';
import { Modal, Button } from '@/components/common';
import { productoService } from '@/services';
import type { Producto, TipoDetalle } from '@/types';

interface ProductSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (producto: Producto, cantidad: number, tipo: TipoDetalle) => void;
}

export const ProductSearchModal: React.FC<ProductSearchModalProps> = ({
  isOpen,
  onClose,
  onSelect,
}) => {
  const [query, setQuery] = useState('');
  const [productos, setProductos] = useState<Producto[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [cantidad, setCantidad] = useState(1);
  const [tipo, setTipo] = useState<TipoDetalle>('Venta');

  const searchProductos = useCallback(async () => {
    if (query.length < 2) {
      setProductos([]);
      return;
    }
    setIsLoading(true);
    try {
      const results = await productoService.search(query);
      setProductos(results);
    } catch {
      setProductos([]);
    } finally {
      setIsLoading(false);
    }
  }, [query]);

  useEffect(() => {
    const timer = setTimeout(searchProductos, 300);
    return () => clearTimeout(timer);
  }, [searchProductos]);

  const handleAdd = () => {
    const producto = productos.find((p) => p.id === selectedId);
    if (producto) {
      onSelect(producto, cantidad, tipo);
      handleReset();
    }
  };

  const handleReset = () => {
    setQuery('');
    setProductos([]);
    setSelectedId(null);
    setCantidad(1);
    setTipo('Venta');
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleReset}
      title="Buscar Producto"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={handleReset}>
            Cancelar
          </Button>
          <Button
            onClick={handleAdd}
            disabled={!selectedId || cantidad < 1}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Agregar al Pedido
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por nombre, codigo SAP o molecula..."
            className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20 focus:border-blue-700"
            autoFocus
          />
        </div>

        <div className="max-h-64 overflow-y-auto space-y-2">
          {isLoading ? (
            <div className="py-8 text-center text-slate-500 text-sm">
              Buscando productos...
            </div>
          ) : productos.length === 0 && query.length >= 2 ? (
            <div className="py-8 text-center text-slate-500 text-sm">
              No se encontraron productos
            </div>
          ) : (
            productos.map((p) => (
              <button
                key={p.id}
                onClick={() => setSelectedId(p.id)}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left cursor-pointer transition-colors ${
                  selectedId === p.id
                    ? 'border-blue-700 bg-blue-50'
                    : 'border-slate-200 hover:bg-slate-50'
                }`}
              >
                <div className="p-2 bg-blue-100 rounded-lg flex-shrink-0">
                  <Pill className="w-4 h-4 text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900">{p.nombre}</p>
                  <p className="text-xs text-slate-500">
                    {p.codigo_sap} - {p.molecula} - {p.distribuidor}
                  </p>
                </div>
                <span className="text-sm font-semibold text-slate-900">
                  S/ {p.precio_vvf.toFixed(2)}
                </span>
              </button>
            ))
          )}
        </div>

        {selectedId && (
          <div className="flex items-center gap-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <div className="flex-1">
              <label htmlFor="modal-cantidad" className="block text-sm font-medium text-slate-700 mb-1">
                Cantidad
              </label>
              <input
                id="modal-cantidad"
                type="number"
                min={1}
                value={cantidad}
                onChange={(e) => setCantidad(Math.max(1, Number(e.target.value)))}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20"
              />
            </div>
            <div className="flex-1">
              <label htmlFor="modal-tipo" className="block text-sm font-medium text-slate-700 mb-1">
                Tipo
              </label>
              <select
                id="modal-tipo"
                value={tipo}
                onChange={(e) => setTipo(e.target.value as TipoDetalle)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm cursor-pointer bg-white focus:outline-none focus:ring-2 focus:ring-blue-700/20"
              >
                <option value="Venta">Venta</option>
                <option value="Bonificacion">Bonificacion</option>
              </select>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
