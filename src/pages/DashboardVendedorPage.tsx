import React from 'react';
import {
  ShoppingBag,
  Clock,
  PackageX,
  DollarSign,
  Check,
  Send,
  XCircle,
  RotateCcw,
  Calculator,
} from 'lucide-react';
import { useDashboard } from '@/hooks';
import { DashboardKPICard } from '@/components';
import { Card } from '@/components/common';
import { cn, formatNumber, timeAgo } from '@/utils';

const activityIcons: Record<string, React.ReactNode> = {
  pedido_aprobado: <Check className="w-4 h-4 text-green-600" />,
  pedido_enviado: <Send className="w-4 h-4 text-blue-600" />,
  pedido_rechazado: <XCircle className="w-4 h-4 text-red-600" />,
  devolucion_registrada: <RotateCcw className="w-4 h-4 text-yellow-600" />,
  comision_calculada: <Calculator className="w-4 h-4 text-purple-600" />,
};

const activityBgs: Record<string, string> = {
  pedido_aprobado: 'bg-green-50',
  pedido_enviado: 'bg-blue-50',
  pedido_rechazado: 'bg-red-50',
  devolucion_registrada: 'bg-yellow-50',
  comision_calculada: 'bg-purple-50',
};

function DashboardSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-slate-200 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-64 bg-slate-200 rounded-xl" />
        <div className="h-64 bg-slate-200 rounded-xl" />
      </div>
    </div>
  );
}

export const DashboardVendedorPage: React.FC = () => {
  const { data, isLoading, error, refetch } = useDashboard();

  if (isLoading) return <DashboardSkeleton />;

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

  if (!data) return null;

  const { estadisticas, top_productos, actividad_reciente } = data;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DashboardKPICard
          title="Pedidos Totales"
          value={estadisticas.total_pedidos}
          icon={<ShoppingBag className="w-4 h-4 text-blue-600" />}
          iconBgClass="bg-blue-50"
          trending={estadisticas.variacion_mes_anterior}
        />
        <DashboardKPICard
          title="En Aprobacion"
          value={estadisticas.pedidos_pendientes}
          icon={<Clock className="w-4 h-4 text-yellow-600" />}
          iconBgClass="bg-yellow-50"
          subtitle="Requieren revision"
        />
        <DashboardKPICard
          title="Devoluciones"
          value={data.devoluciones_mes}
          icon={<PackageX className="w-4 h-4 text-red-600" />}
          iconBgClass="bg-red-50"
          trending={data.variacion_devoluciones}
        />
        <DashboardKPICard
          title="Comisiones"
          value={data.comisiones_acumuladas}
          icon={<DollarSign className="w-4 h-4 text-green-600" />}
          iconBgClass="bg-green-50"
          isCurrency
          subtitle="Mes actual"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pedidos por Estado */}
        <Card>
          <h3 className="text-base font-semibold text-slate-900 mb-4">
            Pedidos por Estado
          </h3>
          <div className="space-y-3">
            {[
              {
                label: 'Aprobados',
                value: estadisticas.pedidos_aprobados,
                pct: estadisticas.porcentaje_aprobados,
                color: 'bg-green-500',
                dot: 'bg-green-500',
              },
              {
                label: 'Pendientes',
                value: estadisticas.pedidos_pendientes,
                pct: estadisticas.porcentaje_pendientes,
                color: 'bg-yellow-500',
                dot: 'bg-yellow-500',
              },
              {
                label: 'Rechazados',
                value: estadisticas.pedidos_rechazados,
                pct: estadisticas.porcentaje_rechazados,
                color: 'bg-red-500',
                dot: 'bg-red-500',
              },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <div className={cn('w-3 h-3 rounded-full', item.dot)} />
                  <span className="text-sm text-slate-600">{item.label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">
                    {formatNumber(item.value)}
                  </span>
                  <div className="w-32 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={cn('h-full rounded-full', item.color)}
                      style={{ width: `${item.pct}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Top Productos */}
        <Card>
          <h3 className="text-base font-semibold text-slate-900 mb-4">
            Top 5 Productos Vendidos
          </h3>
          <div className="space-y-3">
            {top_productos.map((prod) => (
              <div
                key={prod.codigo_sap}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {prod.nombre}
                  </p>
                  <p className="text-xs text-slate-500">{prod.codigo_sap}</p>
                </div>
                <span className="text-sm font-semibold text-blue-700">
                  {formatNumber(prod.unidades_vendidas)} unid.
                </span>
              </div>
            ))}
            {top_productos.length === 0 && (
              <p className="text-sm text-slate-500 text-center py-4">
                Sin datos para este periodo
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* Actividad Reciente */}
      <Card padding="none">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-base font-semibold text-slate-900">
            Actividad Reciente
          </h3>
        </div>
        <div className="divide-y divide-slate-100">
          {actividad_reciente.map((act) => (
            <div
              key={act.id}
              className="p-4 flex items-center gap-4 hover:bg-slate-50 transition-colors"
            >
              <div
                className={cn(
                  'p-2 rounded-lg flex-shrink-0',
                  activityBgs[act.tipo] ?? 'bg-slate-50'
                )}
              >
                {activityIcons[act.tipo] ?? (
                  <Check className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {act.descripcion}
                </p>
              </div>
              <span className="text-xs text-slate-500 whitespace-nowrap">
                {timeAgo(act.fecha)}
              </span>
            </div>
          ))}
          {actividad_reciente.length === 0 && (
            <div className="p-8 text-center text-sm text-slate-500">
              No hay actividad reciente
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};
