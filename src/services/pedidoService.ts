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
    const { data } = await api.get<PaginatedResponse<Pedido>>('/api/pedidos', {
      params: filters,
    });
    return data;
  },

  async getById(id: string): Promise<Pedido> {
    const { data } = await api.get<Pedido>(`/api/pedidos/${id}`);
    return data;
  },

  async create(pedido: CreatePedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>('/api/pedidos', pedido);
    return data;
  },

  async saveDraft(pedido: CreatePedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>('/api/pedidos/borrador', pedido);
    return data;
  },

  async update(id: string, pedido: Partial<CreatePedidoRequest>): Promise<Pedido> {
    const { data } = await api.put<Pedido>(`/api/pedidos/${id}`, pedido);
    return data;
  },

  async approve(request: ApprovePedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>(
      `/api/pedidos/${request.pedido_id}/aprobar`
    );
    return data;
  },

  async reject(request: RejectPedidoRequest): Promise<Pedido> {
    const { data } = await api.post<Pedido>(
      `/api/pedidos/${request.pedido_id}/rechazar`,
      { motivo_rechazo: request.motivo_rechazo }
    );
    return data;
  },

  async getPendientes(filters?: FilterConfig): Promise<PaginatedResponse<Pedido>> {
    const { data } = await api.get<PaginatedResponse<Pedido>>(
      '/api/pedidos/pendientes',
      { params: filters }
    );
    return data;
  },

  async getDashboard(): Promise<DashboardData> {
    const { data } = await api.get<DashboardData>('/api/pedidos/dashboard');
    return data;
  },

  async exportExcel(filters?: FilterConfig): Promise<Blob> {
    const { data } = await api.get('/api/pedidos/export/excel', {
      params: filters,
      responseType: 'blob',
    });
    return data as Blob;
  },

  async downloadPdf(id: string): Promise<Blob> {
    const { data } = await api.get(`/api/pedidos/${id}/pdf`, {
      responseType: 'blob',
    });
    return data as Blob;
  },
};
