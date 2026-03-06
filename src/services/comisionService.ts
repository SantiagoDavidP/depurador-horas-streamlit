import api from './api';
import type {
  ComisionResumen,
  CalculoComisionRequest,
} from '@/types';

export const comisionService = {
  async getResumen(mes: number, anio: number): Promise<ComisionResumen> {
    const { data } = await api.get<ComisionResumen>('/api/comisiones/resumen', {
      params: { mes, anio },
    });
    return data;
  },

  async ejecutarCalculo(request: CalculoComisionRequest): Promise<ComisionResumen> {
    const { data } = await api.post<ComisionResumen>(
      '/api/comisiones/calcular',
      request
    );
    return data;
  },

  async aprobarPago(comisionId: string): Promise<void> {
    await api.post(`/api/comisiones/${comisionId}/aprobar`);
  },

  async exportExcel(mes: number, anio: number): Promise<Blob> {
    const { data } = await api.get('/api/comisiones/export/excel', {
      params: { mes, anio },
      responseType: 'blob',
    });
    return data as Blob;
  },
};
