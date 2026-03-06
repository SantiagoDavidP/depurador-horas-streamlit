import React, { useState } from 'react';
import {
  Building2,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Eye,
} from 'lucide-react';
import { cn, formatCurrency } from '@/utils';
import { Button } from '@/components/common';
import type { ComisionDistribuidor } from '@/types';

interface CommissionCalculatorCardProps {
  distribuidor: ComisionDistribuidor;
  colorScheme: 'blue' | 'purple';
  onApprove?: () => void;
  onViewDetail?: () => void;
}

const colorMap = {
  blue: {
    headerBg: 'from-blue-50 to-transparent',
    iconBg: 'bg-blue-100',
    iconColor: 'text-blue-600',
    accentColor: 'text-green-600',
  },
  purple: {
    headerBg: 'from-purple-50 to-transparent',
    iconBg: 'bg-purple-100',
    iconColor: 'text-purple-600',
    accentColor: 'text-green-600',
  },
};

export const CommissionCalculatorCard: React.FC<CommissionCalculatorCardProps> = ({
  distribuidor,
  colorScheme,
  onApprove,
  onViewDetail,
}) => {
  const [expanded, setExpanded] = useState(false);
  const colors = colorMap[colorScheme];

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div
        className={cn(
          'p-6 border-b border-slate-200 bg-gradient-to-r',
          colors.headerBg
        )}
      >
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={cn('p-3 rounded-xl', colors.iconBg)}>
              <Building2 className={cn('w-6 h-6', colors.iconColor)} />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900">
                {distribuidor.distribuidor}
              </h3>
              <p className="text-sm text-slate-500">
                RUC: {distribuidor.distribuidor_ruc}
              </p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-sm text-slate-500">Comision Periodo</p>
            <p className={cn('text-2xl font-bold', colors.accentColor)}>
              {formatCurrency(distribuidor.comision_total)}
            </p>
          </div>
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <p className="text-xs text-slate-500">Ventas Totales</p>
            <p className="text-sm font-semibold text-slate-900">
              {formatCurrency(distribuidor.ventas_periodo)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500">% Comision</p>
            <p className="text-sm font-semibold text-slate-900">
              {distribuidor.porcentaje_comision}%
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Recuperos</p>
            <p className="text-sm font-semibold text-red-600">
              -{formatCurrency(distribuidor.recuperos)}
            </p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Neto a Pagar</p>
            <p className="text-sm font-bold text-green-600">
              {formatCurrency(distribuidor.neto_pagar)}
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm font-medium text-blue-700 mb-4 cursor-pointer hover:underline"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" /> Ocultar detalle
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" /> Ver detalle de calculo
            </>
          )}
        </button>

        {expanded && (
          <div className="border border-slate-200 rounded-lg overflow-hidden mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-200">
                  <th className="text-left px-4 py-2.5 font-medium text-slate-500">
                    Concepto
                  </th>
                  <th className="text-right px-4 py-2.5 font-medium text-slate-500">
                    Base
                  </th>
                  <th className="text-right px-4 py-2.5 font-medium text-slate-500">
                    %
                  </th>
                  <th className="text-right px-4 py-2.5 font-medium text-slate-500">
                    Monto
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {distribuidor.detalles.map((det, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 text-slate-900">
                      {det.concepto}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-700">
                      {formatCurrency(det.base)}
                    </td>
                    <td className="px-4 py-2.5 text-right text-slate-700">
                      {det.porcentaje}%
                    </td>
                    <td
                      className={cn(
                        'px-4 py-2.5 text-right font-medium',
                        det.es_deduccion ? 'text-red-600' : 'text-slate-900'
                      )}
                    >
                      {det.es_deduccion ? '-' : ''}
                      {formatCurrency(det.monto)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-slate-50 border-t border-slate-200">
                  <td
                    colSpan={3}
                    className="px-4 py-2.5 font-semibold text-slate-900"
                  >
                    Total Neto
                  </td>
                  <td className="px-4 py-2.5 text-right font-bold text-green-600">
                    {formatCurrency(distribuidor.neto_pagar)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3">
          {onViewDetail && (
            <Button
              variant="outline"
              leftIcon={<Eye className="w-4 h-4" />}
              onClick={onViewDetail}
            >
              Ver Detalle
            </Button>
          )}
          {onApprove && (
            <Button
              leftIcon={<CheckCircle className="w-4 h-4" />}
              onClick={onApprove}
              className="bg-green-600 hover:bg-green-700 shadow-green-200"
            >
              Aprobar Pago
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
