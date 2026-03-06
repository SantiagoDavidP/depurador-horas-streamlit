import React, { useState } from 'react';
import {
  TrendingUp,
  Users,
  Building2,
  Package,
  MapPin,
  RefreshCw,
  Share2,
  Maximize2,
  Download,
  Calendar,
  Filter,
  ChevronDown,
  BarChart3,
  PieChart,
} from 'lucide-react';
import { Card, Button } from '@/components/common';
import { cn, formatCurrency, formatNumber } from '@/utils';

type ReportTab =
  | 'ventas_general'
  | 'por_vendedor'
  | 'por_distribuidor'
  | 'por_producto'
  | 'por_region';

const tabs: Array<{ key: ReportTab; label: string; icon: React.ReactNode }> = [
  { key: 'ventas_general', label: 'Ventas General', icon: <TrendingUp className="w-4 h-4" /> },
  { key: 'por_vendedor', label: 'Por Vendedor', icon: <Users className="w-4 h-4" /> },
  { key: 'por_distribuidor', label: 'Por Distribuidor', icon: <Building2 className="w-4 h-4" /> },
  { key: 'por_producto', label: 'Por Producto', icon: <Package className="w-4 h-4" /> },
  { key: 'por_region', label: 'Por Region', icon: <MapPin className="w-4 h-4" /> },
];

const mockKPIs = [
  { label: 'VENTAS TOTALES', value: 428500, isCurrency: true, trend: '+15.2%', trendUp: true },
  { label: 'PEDIDOS PROCESADOS', value: 1247, isCurrency: false, trend: '+18.3%', trendUp: true },
  { label: 'TASA APROBACION', value: 91.5, isCurrency: false, isPercent: true, trend: '-2.1%', trendUp: false },
  { label: 'DEVOLUCIONES', value: 84, isCurrency: false, trend: '-5.0%', trendUp: true },
];

const mockMonthlyData = [
  { month: 'Sep', value: 280000 },
  { month: 'Oct', value: 320000 },
  { month: 'Nov', value: 350000 },
  { month: 'Dic', value: 310000 },
  { month: 'Ene', value: 380000 },
  { month: 'Feb', value: 428500 },
];

const mockDistribution = [
  { name: 'Dimexa', percentage: 58, color: 'bg-blue-500' },
  { name: 'Quimica Suiza', percentage: 42, color: 'bg-purple-500' },
];

const mockTopProducts = [
  { rank: 1, name: 'Paracetamol 500mg', units: 2450 },
  { rank: 2, name: 'Ibuprofeno 400mg', units: 1890 },
  { rank: 3, name: 'Amoxicilina 500mg', units: 1654 },
  { rank: 4, name: 'Omeprazol 20mg', units: 1432 },
];

const mockReportGallery = [
  { title: 'Rendimiento por Vendedor', icon: <Users className="w-8 h-8 text-blue-600" />, bg: 'bg-blue-50' },
  { title: 'Analisis de Comisiones', icon: <PieChart className="w-8 h-8 text-green-600" />, bg: 'bg-green-50' },
  { title: 'Devoluciones & Recuperos', icon: <BarChart3 className="w-8 h-8 text-red-600" />, bg: 'bg-red-50' },
];

export const PowerBIReportsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ReportTab>('ventas_general');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const maxValue = Math.max(...mockMonthlyData.map((d) => d.value));

  return (
    <div className="space-y-6">
      {/* Report Tabs */}
      <Card padding="none">
        <div className="flex items-center gap-1 p-2 border-b border-slate-200 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg cursor-pointer whitespace-nowrap transition-colors',
                activeTab === tab.key
                  ? 'text-white bg-blue-700'
                  : 'text-slate-600 hover:bg-slate-100'
              )}
            >
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Power BI Content Area */}
        <div className={cn('relative', isFullscreen ? 'fixed inset-0 z-50 bg-white' : '')}>
          <div className="bg-gradient-to-br from-slate-50 to-slate-100 p-6">
            {/* Filters Bar */}
            <div className="flex items-center gap-3 mb-4 pb-4 border-b border-slate-300">
              <div className="flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 rounded shadow-sm cursor-pointer">
                <Calendar className="w-4 h-4 text-slate-500" />
                <span className="text-sm text-slate-700">Ultimo Trimestre</span>
                <ChevronDown className="w-4 h-4 text-slate-400" />
              </div>
              <div className="flex items-center gap-2 px-3 py-2 bg-white border border-slate-300 rounded shadow-sm cursor-pointer">
                <Filter className="w-4 h-4 text-slate-500" />
                <span className="text-sm text-slate-700">
                  Todos los distribuidores
                </span>
                <ChevronDown className="w-4 h-4 text-slate-400" />
              </div>
              <div className="ml-auto flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<RefreshCw className="w-4 h-4" />}
                >
                  Actualizar
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<Share2 className="w-4 h-4" />}
                >
                  Compartir
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<Download className="w-4 h-4" />}
                >
                  PDF
                </Button>
                <button
                  onClick={() => setIsFullscreen(!isFullscreen)}
                  className="p-2 text-slate-600 hover:bg-slate-200 rounded cursor-pointer transition-colors"
                  aria-label="Pantalla completa"
                >
                  <Maximize2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Dashboard Grid */}
            <div className="grid grid-cols-12 gap-4">
              {/* KPI Column */}
              <div className="col-span-12 lg:col-span-3 space-y-4">
                {mockKPIs.map((kpi) => (
                  <div
                    key={kpi.label}
                    className="bg-white rounded-lg shadow-md border border-slate-200 p-4"
                  >
                    <p className="text-xs font-medium text-slate-500 mb-2">
                      {kpi.label}
                    </p>
                    <p className="text-2xl font-bold text-slate-900 mb-1">
                      {kpi.isCurrency
                        ? formatCurrency(kpi.value)
                        : kpi.isPercent
                          ? `${kpi.value}%`
                          : formatNumber(kpi.value)}
                    </p>
                    <div
                      className={cn(
                        'flex items-center gap-1 text-xs',
                        kpi.trendUp ? 'text-green-600' : 'text-red-600'
                      )}
                    >
                      <TrendingUp className="w-3 h-3" />
                      <span>{kpi.trend}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Main Chart */}
              <div className="col-span-12 lg:col-span-6">
                <div className="bg-white rounded-lg shadow-md border border-slate-200 p-4 h-full">
                  <p className="text-xs font-medium text-slate-500 mb-4">
                    EVOLUCION DE VENTAS MENSUAL
                  </p>
                  <div className="flex items-end gap-3 h-48">
                    {mockMonthlyData.map((d, i) => {
                      const height = (d.value / maxValue) * 100;
                      const isLast = i === mockMonthlyData.length - 1;
                      return (
                        <div
                          key={d.month}
                          className="flex-1 flex flex-col items-center gap-1"
                        >
                          <span className="text-xs font-medium text-slate-700">
                            {formatCurrency(d.value).replace('PEN', 'S/')}
                          </span>
                          <div
                            className={cn(
                              'w-full rounded-t-md transition-all',
                              isLast
                                ? 'bg-gradient-to-t from-blue-600 to-blue-400'
                                : 'bg-gradient-to-t from-blue-400 to-blue-300'
                            )}
                            style={{ height: `${height}%` }}
                          />
                          <span className="text-xs text-slate-500">
                            {d.month}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* Right Column */}
              <div className="col-span-12 lg:col-span-3 space-y-4">
                {/* Donut Chart Mockup */}
                <div className="bg-white rounded-lg shadow-md border border-slate-200 p-4">
                  <p className="text-xs font-medium text-slate-500 mb-4">
                    VENTAS POR DISTRIBUIDOR
                  </p>
                  <div className="flex items-center justify-center mb-4">
                    <div className="relative w-28 h-28">
                      <svg viewBox="0 0 36 36" className="w-full h-full">
                        <circle
                          cx="18"
                          cy="18"
                          r="15.915"
                          fill="none"
                          stroke="#e2e8f0"
                          strokeWidth="3"
                        />
                        <circle
                          cx="18"
                          cy="18"
                          r="15.915"
                          fill="none"
                          stroke="#3B82F6"
                          strokeWidth="3"
                          strokeDasharray="58 42"
                          strokeDashoffset="25"
                        />
                        <circle
                          cx="18"
                          cy="18"
                          r="15.915"
                          fill="none"
                          stroke="#8B5CF6"
                          strokeWidth="3"
                          strokeDasharray="42 58"
                          strokeDashoffset="67"
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {mockDistribution.map((d) => (
                      <div
                        key={d.name}
                        className="flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <div
                            className={cn('w-3 h-3 rounded-full', d.color)}
                          />
                          <span className="text-xs text-slate-700">
                            {d.name}
                          </span>
                        </div>
                        <span className="text-xs font-semibold text-slate-900">
                          {d.percentage}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Top Products */}
                <div className="bg-white rounded-lg shadow-md border border-slate-200 p-4">
                  <p className="text-xs font-medium text-slate-500 mb-3">
                    TOP PRODUCTOS
                  </p>
                  <div className="space-y-2">
                    {mockTopProducts.map((p) => (
                      <div
                        key={p.rank}
                        className="flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 text-xs font-semibold flex items-center justify-center">
                            {p.rank}
                          </span>
                          <span className="text-xs text-slate-700 truncate max-w-[120px]">
                            {p.name}
                          </span>
                        </div>
                        <span className="text-xs font-semibold text-slate-900">
                          {formatNumber(p.units)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M4 4h7v7H4V4zM4 13h7v7H4v-7zM13 4h7v7h-7V4zM13 13h7v7h-7v-7z"
                    fill="#F2C811"
                  />
                </svg>
                <span>Powered by Microsoft Power BI</span>
              </div>
              <span>Ultima actualizacion: hace 15 min</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Report Gallery */}
      <div>
        <h3 className="text-base font-semibold text-slate-900 mb-4">
          Reportes Disponibles
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {mockReportGallery.map((report) => (
            <Card
              key={report.title}
              className="hover:shadow-md transition-shadow cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <div
                  className={cn(
                    'p-4 rounded-xl flex-shrink-0',
                    report.bg
                  )}
                >
                  {report.icon}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    {report.title}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Ver reporte completo
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
};
