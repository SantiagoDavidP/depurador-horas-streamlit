export type EstadoPedido = 'Borrador' | 'Enviado' | 'Aprobado' | 'Rechazado';
export type TipoDetalle = 'Venta' | 'Bonificacion';

export interface DetallePedido {
  id: string;
  pedido_id: string;
  producto_id: string;
  producto_nombre: string;
  producto_codigo_sap: string;
  cantidad: number;
  precio_unitario: number;
  bonificacion: number;
  subtotal: number;
  tipo: TipoDetalle;
}

export interface Pedido {
  id: string;
  codigo_pedido: string;
  fecha: string;
  cliente_ruc: string;
  cliente_razon_social: string;
  representante: string;
  condicion_pago: string;
  estado: EstadoPedido;
  total: number;
  subtotal: number;
  igv: number;
  vendedor_id: string;
  vendedor_nombre: string;
  vendedor_email: string;
  detalles: DetallePedido[];
  motivo_rechazo?: string;
  aprobado_por?: string;
  fecha_aprobacion?: string;
  created_at: string;
  updated_at: string;
}

export interface CreatePedidoRequest {
  cliente_ruc: string;
  representante: string;
  condicion_pago: string;
  detalles: CreateDetallePedido[];
}

export interface CreateDetallePedido {
  producto_id: string;
  cantidad: number;
  tipo: TipoDetalle;
}

export interface ApprovePedidoRequest {
  pedido_id: string;
}

export interface RejectPedidoRequest {
  pedido_id: string;
  motivo_rechazo: string;
}

export interface PedidoEstadisticas {
  total_pedidos: number;
  pedidos_aprobados: number;
  pedidos_pendientes: number;
  pedidos_rechazados: number;
  total_ventas: number;
  porcentaje_aprobados: number;
  porcentaje_pendientes: number;
  porcentaje_rechazados: number;
  variacion_mes_anterior: number;
}

export interface TopProducto {
  codigo_sap: string;
  nombre: string;
  unidades_vendidas: number;
}

export interface ActividadReciente {
  id: string;
  tipo: 'pedido_aprobado' | 'pedido_enviado' | 'pedido_rechazado' | 'devolucion_registrada' | 'comision_calculada';
  descripcion: string;
  fecha: string;
  icono: string;
}

export interface DashboardData {
  estadisticas: PedidoEstadisticas;
  top_productos: TopProducto[];
  actividad_reciente: ActividadReciente[];
  comisiones_acumuladas: number;
  devoluciones_mes: number;
  variacion_devoluciones: number;
}
