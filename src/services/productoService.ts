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
      '/api/products',
      { params }
    );
    return data;
  },

  async getById(id: string): Promise<Producto> {
    const { data } = await api.get<Producto>(`/api/products/${id}`);
    return data;
  },

  async search(query: string): Promise<Producto[]> {
    // El backend no tiene /search — usa el endpoint de lista con param search
    const { data } = await api.get<{ items: Producto[]; total: number }>('/api/products', {
      params: { search: query, limit: 20 },
    });
    return data.items;
  },

  async getDevolvibles(pedidoId: string): Promise<Producto[]> {
    const { data } = await api.get<Producto[]>(
      `/api/products/devolvibles/${pedidoId}`
    );
    return data;
  },
};
