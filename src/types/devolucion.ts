export type EstadoDevolucion = 'En Proceso' | 'Aprobada' | 'Rechazada';

export type RazonDevolucion =
  | 'Producto dañado'
  | 'Fecha de vencimiento proxima'
  | 'Error en el pedido'
  | 'Cliente rechazo entrega'
  | 'Defecto de fabricacion';

export interface Devolucion {
  id: string;
  codigo_devolucion: string;
  pedido_id: string;
  pedido_codigo: string;
  producto_id: string;
  producto_nombre: string;
  producto_codigo_sap: string;
  lote: string;
  numero_factura: string;
  cantidad: number;
  razon: RazonDevolucion;
  estado: EstadoDevolucion;
  valorizado: number;
  observaciones?: string;
  cliente_ruc: string;
  cliente_razon_social: string;
  representante: string;
  fecha_pedido: string;
  created_at: string;
  updated_at: string;
}

export interface ProductoDevolucion {
  producto_id: string;
  producto_nombre: string;
  producto_codigo_sap: string;
  cantidad: number;
  lote: string;
  razon: RazonDevolucion;
  precio_unitario: number;
  valorizado: number;
}

export interface CreateDevolucionRequest {
  pedido_id: string;
  numero_factura: string;
  productos: CreateProductoDevolucion[];
  observaciones?: string;
}

export interface CreateProductoDevolucion {
  producto_id: string;
  cantidad: number;
  lote: string;
  razon: RazonDevolucion;
}
