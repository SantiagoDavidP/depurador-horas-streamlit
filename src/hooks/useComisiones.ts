import { useState, useCallback } from 'react';
import { comisionService } from '@/services';
import { useNotificationStore } from '@/store';
import type { ComisionResumen } from '@/types';

export function useComisiones() {
  const [data, setData] = useState<ComisionResumen | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const addToast = useNotificationStore((s) => s.addToast);

  const fetchResumen = useCallback(
    async (mes: number, anio: number) => {
      setIsLoading(true);
      setError(null);
      try {
        const result = await comisionService.getResumen(mes, anio);
        setData(result);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al cargar comisiones';
        setError(msg);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const ejecutarCalculo = useCallback(
    async (mes: number, anio: number) => {
      setIsCalculating(true);
      try {
        const result = await comisionService.ejecutarCalculo({ mes, anio });
        setData(result);
        addToast({
          type: 'success',
          title: 'Calculo ejecutado',
          message: 'Las comisiones se han calculado correctamente',
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al calcular comisiones';
        addToast({ type: 'error', title: 'Error', message: msg });
      } finally {
        setIsCalculating(false);
      }
    },
    [addToast]
  );

  const exportExcel = useCallback(
    async (mes: number, anio: number) => {
      try {
        const blob = await comisionService.exportExcel(mes, anio);
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `comisiones_${anio}_${String(mes).padStart(2, '0')}.xlsx`;
        link.click();
        window.URL.revokeObjectURL(url);
        addToast({ type: 'success', title: 'Excel descargado' });
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al exportar';
        addToast({ type: 'error', title: 'Error', message: msg });
      }
    },
    [addToast]
  );

  return {
    data,
    isLoading,
    isCalculating,
    error,
    fetchResumen,
    ejecutarCalculo,
    exportExcel,
  };
}
