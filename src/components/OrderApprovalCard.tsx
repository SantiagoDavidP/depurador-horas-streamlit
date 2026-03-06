import React, { useState } from 'react';
import {
  ShoppingBag,
  Pill,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { cn, formatCurrency, formatDateTime } from '@/utils';
import { StatusBadge, Button, Modal } from '@/components/common';
import type { Pedido } from '@/types';

interface OrderApprovalCardProps {
  pedido: Pedido;
  onApprove: (id: string) => void;
  onReject: (id: string, motivo: string) => void;
  isProcessing?: boolean;
}

export const OrderApprovalCard: React.FC<OrderApprovalCardProps> = ({
  pedido,
  onApprove,
  onReject,
  isProcessing,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [motivoRechazo, setMotivoRechazo] = useState('');
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const handleReject = () => {
    if (motivoRechazo.trim()) {
      onReject(pedido.id, motivoRechazo);
      setShowRejectModal(false);
      setMotivoRechazo('');
    }
  };

  const handleApprove = () => {
    onApprove(pedido.id);
    setShowConfirmModal(false);
  };

  return (
    <>
      <div className="bg-white rounded-xl border-2 border-yellow-200 p-6 hover:shadow-lg transition-shadow">
        <div className="flex flex-col md:flex-row items-start justify-between mb-4 gap-4">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-yellow-50 rounded-xl flex-shrink-0">
              <ShoppingBag className="w-6 h-6 text-yellow-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                {pedido.codigo_pedido}
              </h3>
              <p className="text-sm text-slate-500 mt-0.5">
                Registrado el {formatDateTime(pedido.created_at)}
              </p>
              <div className="mt-2">
                <StatusBadge label={pedido.estado} />
              </div>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-500">Monto Total</p>
            <p className="text-2xl font-bold text-slate-900">
              {formatCurrency(pedido.total)}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg mb-4">
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Cliente</p>
            <p className="text-sm font-semibold text-slate-900">
              {pedido.cliente_razon_social}
            </p>
            <p className="text-xs text-slate-600">RUC: {pedido.cliente_ruc}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Vendedor</p>
            <p className="text-sm font-semibold text-slate-900">
              {pedido.vendedor_nombre}
            </p>
            <p className="text-xs text-slate-600">{pedido.vendedor_email}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">
              Condicion de Pago
            </p>
            <p className="text-sm font-semibold text-slate-900">
              {pedido.condicion_pago}
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm font-medium text-blue-700 mb-4 cursor-pointer hover:underline"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" /> Ocultar productos
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" /> Ver productos ({pedido.detalles.length} items)
            </>
          )}
        </button>

        {expanded && (
          <div className="space-y-2 mb-4">
            {pedido.detalles.map((det) => (
              <div
                key={det.id}
                className={cn(
                  'flex items-center justify-between p-3 rounded-lg',
                  det.tipo === 'Bonificacion'
                    ? 'bg-green-50 border border-green-200'
                    : 'bg-slate-50'
                )}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'p-2 rounded-lg',
                      det.tipo === 'Bonificacion'
                        ? 'bg-green-100'
                        : 'bg-blue-100'
                    )}
                  >
                    <Pill
                      className={cn(
                        'w-4 h-4',
                        det.tipo === 'Bonificacion'
                          ? 'text-green-600'
                          : 'text-blue-600'
                      )}
                    />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">
                      {det.producto_nombre}
                    </p>
                    <p className="text-xs text-slate-500">
                      {det.producto_codigo_sap}
                      {det.tipo === 'Bonificacion' && ' - Bonificacion'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-slate-900">
                    {det.cantidad} unid.
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatCurrency(det.precio_unitario)} c/u
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center gap-3 pt-4 border-t border-slate-200">
          <Button
            variant="primary"
            leftIcon={<CheckCircle className="w-4 h-4" />}
            onClick={() => setShowConfirmModal(true)}
            isLoading={isProcessing}
            className="w-full sm:w-auto bg-green-600 hover:bg-green-700 shadow-green-200"
          >
            Aprobar Pedido
          </Button>
          <Button
            variant="danger"
            leftIcon={<XCircle className="w-4 h-4" />}
            onClick={() => setShowRejectModal(true)}
            isLoading={isProcessing}
            className="w-full sm:w-auto"
          >
            Rechazar
          </Button>
        </div>
      </div>

      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Confirmar Aprobacion"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowConfirmModal(false)}>
              Cancelar
            </Button>
            <Button
              onClick={handleApprove}
              className="bg-green-600 hover:bg-green-700 shadow-green-200"
            >
              Si, Aprobar
            </Button>
          </>
        }
      >
        <p className="text-sm text-slate-700">
          Confirme que desea aprobar el pedido{' '}
          <strong>{pedido.codigo_pedido}</strong> por un monto de{' '}
          <strong>{formatCurrency(pedido.total)}</strong>. Se notificara al
          distribuidor y al vendedor.
        </p>
      </Modal>

      <Modal
        isOpen={showRejectModal}
        onClose={() => setShowRejectModal(false)}
        title="Rechazar Pedido"
        footer={
          <>
            <Button variant="secondary" onClick={() => setShowRejectModal(false)}>
              Cancelar
            </Button>
            <Button
              variant="danger"
              onClick={handleReject}
              disabled={!motivoRechazo.trim()}
            >
              Rechazar Pedido
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-700">
            Indique el motivo de rechazo para el pedido{' '}
            <strong>{pedido.codigo_pedido}</strong>.
          </p>
          <textarea
            value={motivoRechazo}
            onChange={(e) => setMotivoRechazo(e.target.value)}
            placeholder="Escriba el motivo de rechazo..."
            rows={4}
            className="w-full px-3 py-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20 focus:border-blue-700 resize-none"
          />
        </div>
      </Modal>
    </>
  );
};
