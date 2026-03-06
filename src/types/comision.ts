export type EstadoComision = 'Pendiente' | 'Calculada' | 'Aprobada';

export interface Comision {
  id: string;
  distribuidor: string;
  distribuidor_ruc: string;
  porcentaje: number;
  monto_calculado: number;
  mes_proceso: string;
  estado: EstadoComision;
  ventas_totales: number;
  recuperos: number;
  neto_pagar: number;
  cantidad_pedidos: number;
  cantidad_devoluciones: number;
}

export interface ComisionResumen {
  total_ventas_mes: number;
  comisiones_totales: number;
  recuperos_devoluciones: number;
  variacion_ventas: number;
  cantidad_devoluciones: number;
  distribuidores: ComisionDistribuidor[];
}

export interface ComisionDistribuidor {
  distribuidor: string;
  distribuidor_ruc: string;
  porcentaje_comision: number;
  ventas_periodo: number;
  comision_total: number;
  recuperos: number;
  neto_pagar: number;
  detalles: ComisionDetalle[];
}

export interface ComisionDetalle {
  concepto: string;
  base: number;
  porcentaje: number;
  monto: number;
  es_deduccion: boolean;
}

export interface CalculoComisionRequest {
  mes: number;
  anio: number;
}
