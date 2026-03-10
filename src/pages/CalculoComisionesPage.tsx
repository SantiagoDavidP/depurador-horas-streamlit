import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Percent,
  PackageX,
  Play,
  Download,
  Calendar,
  Info,
} from 'lucide-react';
import { Card, Button } from '@/components/common';
import { CommissionCalculatorCard } from '@/components';
import { useComisiones } from '@/hooks';
import { formatCurrency, formatPercentage } from '@/utils';

const MESES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
];

function buildMesOptions(): Array<{ value: string; label: string }> {
  const now = new Date();
  const options: Array<{ value: string; label: string }> = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const val = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const label = `${MESES[d.getMonth()]} ${d.getFullYear()}`;
    options.push({ value: val, label });
  }
  return options;
}

export const CalculoComisionesPage: React.FC = () => {
  const mesOptions = buildMesOptions();
  const [selectedPeriodo, setSelectedPeriodo] = useState(mesOptions[0].value);
  const { data, isLoading, isCalculating, error, fetchResumen, ejecutarCalculo, exportExcel } =
    useComisiones();

  // "YYYY-MM" → split → ["YYYY","MM"] → primer elemento es el AÑO, segundo es el MES
  const [anio, mes] = selectedPeriodo.split('-').map(Number) as [number, number];

  useEffect(() => {
    fetchResumen(mes, anio);
  }, [mes, anio, fetchResumen]);

  const handleCalcular = () => {
    ejecutarCalculo(mes, anio);
  };

  const handleExport = () => {
    exportExcel(mes, anio);
  };

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-24 bg-slate-200 rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-40 bg-slate-200 rounded-xl" />
          ))}
        </div>
        <div className="h-64 bg-slate-200 rounded-xl" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <p className="text-sm text-red-600 mb-4">{error}</p>
        <button
          onClick={() => fetchResumen(mes, anio)}
          className="px-4 py-2 text-sm font-medium text-blue-700 border border-blue-700 rounded-lg hover:bg-blue-50 cursor-pointer transition-colors"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <Card>
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-semibold text-slate-900 mb-1">
              Periodo de Calculo
            </h3>
            <p className="text-sm text-slate-500">
              Seleccione el mes para calcular comisiones y recuperos
            </p>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={selectedPeriodo}
              onChange={(e) => setSelectedPeriodo(e.target.value)}
              className="px-4 py-2.5 border border-slate-300 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-700/20 cursor-pointer transition-all bg-white"
              aria-label="Seleccionar periodo"
            >
              {mesOptions.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <button
              className="p-2.5 border border-slate-300 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
              aria-label="Abrir calendario"
            >
              <Calendar className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </div>
      </Card>

      {/* Summary Hero Cards */}
      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <Info className="w-5 h-5 opacity-60 cursor-pointer" />
              </div>
              <p className="text-sm font-medium opacity-90 mb-1">
                Total Ventas Mes
              </p>
              <p className="text-3xl font-bold">
                {formatCurrency(data.total_ventas_mes)}
              </p>
              <p className="text-xs opacity-75 mt-2">
                {formatPercentage(data.variacion_ventas)} vs mes anterior
              </p>
            </div>

            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                  <Percent className="w-6 h-6" />
                </div>
                <Info className="w-5 h-5 opacity-60 cursor-pointer" />
              </div>
              <p className="text-sm font-medium opacity-90 mb-1">
                Comisiones Totales
              </p>
              <p className="text-3xl font-bold">
                {formatCurrency(data.comisiones_totales)}
              </p>
              <p className="text-xs opacity-75 mt-2">
                {data.distribuidores.length} distribuidores activos
              </p>
            </div>

            <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-6 text-white shadow-lg">
              <div className="flex items-center justify-between mb-4">
                <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                  <PackageX className="w-6 h-6" />
                </div>
                <Info className="w-5 h-5 opacity-60 cursor-pointer" />
              </div>
              <p className="text-sm font-medium opacity-90 mb-1">
                Recuperos Devoluciones
              </p>
              <p className="text-3xl font-bold">
                {formatCurrency(data.recuperos_devoluciones)}
              </p>
              <p className="text-xs opacity-75 mt-2">
                {data.cantidad_devoluciones} devoluciones procesadas
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3 justify-end">
            <Button
              variant="outline"
              leftIcon={<Download className="w-4 h-4" />}
              onClick={handleExport}
            >
              Exportar Excel
            </Button>
            <Button
              leftIcon={<Play className="w-4 h-4" />}
              onClick={handleCalcular}
              isLoading={isCalculating}
            >
              Ejecutar Calculo
            </Button>
          </div>

          {/* Distributor Cards */}
          <div className="space-y-4">
            {data.distribuidores.map((dist, idx) => (
              <CommissionCalculatorCard
                key={dist.distribuidor}
                distribuidor={dist}
                colorScheme={idx % 2 === 0 ? 'blue' : 'purple'}
                onApprove={() => {
                  /* approve logic */
                }}
                onViewDetail={() => {
                  /* detail modal */
                }}
              />
            ))}
            {data.distribuidores.length === 0 && (
              <div className="text-center py-12 text-slate-500 text-sm">
                No hay datos de comisiones para el periodo seleccionado.
                Ejecute el calculo para generar los resultados.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
