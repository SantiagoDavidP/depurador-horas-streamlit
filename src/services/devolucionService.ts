import api from './api';
import type {
  Devolucion,
  PaginatedResponse,
  FilterConfig,
  CreateDevolucionRequest,
} from '@/types';

export const devolucionService = {
  async list(filters?: FilterConfig): Promise<PaginatedResponse<Devolucion>> {
    const { data } = await api.get<PaginatedResponse<Devolucion>>(
      '/api/devoluciones',
      { params: filters }
    );
    return data;
  },

  async getById(id: string): Promise<Devolucion> {
    const { data } = await api.get<Devolucion>(`/api/devoluciones/${id}`);
    return data;
  },

  async create(devolucion: CreateDevolucionRequest): Promise<Devolucion> {
    const { data } = await api.post<Devolucion>(
      '/api/devoluciones',
      devolucion
    );
    return data;
  },

  async approve(id: string): Promise<Devolucion> {
    const { data } = await api.post<Devolucion>(
      `/api/devoluciones/${id}/aprobar`
    );
    return data;
  },

  async reject(id: string, motivo: string): Promise<Devolucion> {
    const { data } = await api.post<Devolucion>(
      `/api/devoluciones/${id}/rechazar`,
      { motivo }
    );
    return data;
  },
};
