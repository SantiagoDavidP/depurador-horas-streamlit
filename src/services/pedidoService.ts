import api from './api';
import type {
  Pedido,
  PaginatedResponse,
  FilterConfig,
  CreatePedidoRequest,
  ApprovePedidoRequest,
  RejectPedidoRequest,
  DashboardData,
} from '@/types';

export const pedidoService = {
  async list(filters?: FilterConfig): Promise<PaginatedResponse<Pedido>> {
    const { data } = await api.get<PaginatedResponse<Pedido>>('/api/orders', {
      params: filters,
    });
    return data;
  },

  async getById(id: string): Promise<Pedido> {
    const { data } = await api.get<Pedido>(`/api/orders/${id}`);
    return data;
  },

  async create(pedido: CreatePedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>('/api/orders', pedido);
    return data;
  },

  async saveDraft(pedido: CreatePedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>('/api/orders/borrador', pedido);
    return data;
  },

  async update(id: string, pedido: Partial<CreatePedidoRequest>): Promise<Pedido> {
    const { data } = await api.put<Pedido>(`/api/orders/${id}`, pedido);
    return data;
  },

  async approve(request: ApprovePedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>(
      `/api/orders/${request.pedido_id}/approve`
    );
    return data;
  },

  async reject(request: RejectPedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>(
      `/api/orders/${request.pedido_id}/reject`,
      { motivo_rechazo: request.motivo_rechazo }
    );
    return data;
  },

  async getPendientes(filters?: FilterConfig): Promise<PaginatedResponse<Pedido>> {
    const { data } = await api.get<PaginatedResponse<Pedido>>(
      '/api/orders/pending',
      { params: filters }
    );
    return data;
  },

  async getDashboard(): Promise<DashboardData> {
    const { data } = await api.get<DashboardData>('/api/dashboard/me');
    return data;
  },

  async exportExcel(filters?: FilterConfig): Promise<Blob> {
    const { data } = await api.get('/api/orders/export/excel', {
      params: filters,
      responseType: 'blob',
    });
    return data as Blob;
  },

  async downloadPdf(id: string): Promise<Blob> {
    const { data } = await api.get(`/api/orders/${id}/pdf`, {
      responseType: 'blob',
    });
    return data as Blob;
  },
};
