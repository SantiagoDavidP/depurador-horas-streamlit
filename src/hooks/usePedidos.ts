import { useState, useEffect, useCallback } from 'react';
import { pedidoService } from '@/services';
import { useNotificationStore } from '@/store';
import type {
  Pedido,
  PaginatedResponse,
  FilterConfig,
  CreatePedidoRequest,
  DashboardData,
} from '@/types';

export function usePedidos(initialFilters?: FilterConfig) {
  const [data, setData] = useState<PaginatedResponse<Pedido> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterConfig>(initialFilters ?? { page: 1, page_size: 10 });
  const addToast = useNotificationStore((s) => s.addToast);

  const fetchPedidos = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await pedidoService.list(filters);
      setData(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al cargar pedidos';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchPedidos();
  }, [fetchPedidos]);

  const createPedido = useCallback(
    async (pedido: CreatePedidoRequest): Promise<Pedido | null> => {
      try {
        const result = await pedidoService.create(pedido);
        addToast({ type: 'success', title: 'Pedido enviado', message: `Codigo: ${result.codigo_pedido}` });
        await fetchPedidos();
        return result;
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al crear pedido';
        addToast({ type: 'error', title: 'Error', message: msg });
        return null;
      }
    },
    [fetchPedidos, addToast]
  );

  const approvePedido = useCallback(
    async (pedidoId: string) => {
      try {
        await pedidoService.approve({ pedido_id: pedidoId });
        addToast({ type: 'success', title: 'Pedido aprobado' });
        await fetchPedidos();
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al aprobar';
        addToast({ type: 'error', title: 'Error', message: msg });
      }
    },
    [fetchPedidos, addToast]
  );

  const rejectPedido = useCallback(
    async (pedidoId: string, motivo: string) => {
      try {
        await pedidoService.reject({ pedido_id: pedidoId, motivo_rechazo: motivo });
        addToast({ type: 'success', title: 'Pedido rechazado' });
        await fetchPedidos();
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Error al rechazar';
        addToast({ type: 'error', title: 'Error', message: msg });
      }
    },
    [fetchPedidos, addToast]
  );

  return {
    pedidos: data?.items ?? [],
    total: data?.total ?? 0,
    totalPages: data?.total_pages ?? 0,
    isLoading,
    error,
    filters,
    setFilters,
    refetch: fetchPedidos,
    createPedido,
    approvePedido,
    rejectPedido,
  };
}

export function usePedidosPendientes(initialFilters?: FilterConfig) {
  const [data, setData] = useState<PaginatedResponse<Pedido> | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterConfig>(initialFilters ?? { page: 1, page_size: 10 });

  const fetchPendientes = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await pedidoService.getPendientes(filters);
      setData(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al cargar pendientes';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchPendientes();
  }, [fetchPendientes]);

  return {
    pedidos: data?.items ?? [],
    total: data?.total ?? 0,
    totalPages: data?.total_pages ?? 0,
    isLoading,
    error,
    filters,
    setFilters,
    refetch: fetchPendientes,
  };
}

export function useDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await pedidoService.getDashboard();
      setData(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Error al cargar dashboard';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return { data, isLoading, error, refetch: fetchDashboard };
}
