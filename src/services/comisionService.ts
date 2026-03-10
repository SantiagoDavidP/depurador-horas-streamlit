import api from './api';
import type {
  ComisionResumen,
  CalculoComisionRequest,
} from '@/types';

export const comisionService = {
  async getResumen(mes: number, anio: number): Promise<ComisionResumen> {
    const { data } = await api.get<ComisionResumen>('/api/commissions/summary', {
      params: { mes, anio },
    });
    return data;
  },

  async ejecutarCalculo(request: CalculoComisionRequest): Promise<ComisionResumen> {
    // Trigger calculation (GET /calculate persists results to DB)
    await api.get('/api/commissions/calculate', {
      params: { mes: request.mes, anio: request.anio },
    });
    // Fetch updated summary to return frontend-compatible shape
    const { data } = await api.get<ComisionResumen>('/api/commissions/summary', {
      params: { mes: request.mes, anio: request.anio },
    });
    return data;
  },

  async aprobarPago(comisionId: string): Promise<void> {
    await api.post(`/api/commissions/${comisionId}/aprobar`);
  },

  async exportExcel(mes: number, anio: number): Promise<Blob> {
    const { data } = await api.get('/api/commissions/export', {
      params: { mes, anio },
      responseType: 'blob',
    });
    return data as Blob;
  },
};
