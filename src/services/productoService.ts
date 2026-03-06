import api from './api';
import type { Producto, PaginatedResponse } from '@/types';

export const productoService = {
  async list(params?: {
    search?: string;
    distribuidor?: string;
    molecula?: string;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Producto>> {
    const { data } = await api.get<PaginatedResponse<Producto>>(
      '/api/productos',
      { params }
    );
    return data;
  },

  async getById(id: string): Promise<Producto> {
    const { data } = await api.get<Producto>(`/api/productos/${id}`);
    return data;
  },

  async search(query: string): Promise<Producto[]> {
    const { data } = await api.get<Producto[]>('/api/productos/search', {
      params: { q: query },
    });
    return data;
  },

  async getDevolvibles(pedidoId: string): Promise<Producto[]> {
    const { data } = await api.get<Producto[]>(
      `/api/productos/devolvibles/${pedidoId}`
    );
    return data;
  },
};
