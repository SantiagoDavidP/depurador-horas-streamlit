import { useState, useEffect, useCallback } from 'react';
import { devolucionService } from '@/services';
import { useNotificationStore } from '@/store';
import type {
  Devolucion,
  PaginatedResponse,
  FilterConfig,
  CreateDevolucionRequest,
} from '@/types';

export function useDevoluciones(initialFilters?: FilterConfig) {
  const [data, setData] = useState<PaginatedResponse<Devolucion> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterConfig>(
    initialFilters ?? { page: 1, page_size: 10 }
  );
  const addToast = useNotificationStore((s) => s.addToast);

  const fetchDevoluciones = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await devolucionService.list(filters);
      setData(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al cargar devoluciones';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchDevoluciones();
  }, [fetchDevoluciones]);

  const createDevolucion = useCallback(
    async (devolucion: CreateDevolucionRequest): Promise<Devolucion | null> => {
      try {
        const result = await devolucionService.create(devolucion);
        addToast({
          type: 'success',
          title: 'Devolucion registrada',
          message: `Codigo: ${result.codigo_devolucion}`,
        });
        await fetchDevoluciones();
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al registrar devolucion';
        addToast({ type: 'error', title: 'Error', message: msg });
        return null;
      }
    },
    [fetchDevoluciones, addToast]
  );

  return {
    devoluciones: data?.items ?? [],
    total: data?.total ?? 0,
    totalPages: data?.total_pages ?? 0,
    isLoading,
    error,
    filters,
    setFilters,
    refetch: fetchDevoluciones,
    createDevolucion,
  };
}
