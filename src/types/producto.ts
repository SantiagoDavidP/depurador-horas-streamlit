export interface Producto {
  id: string;
  codigo_sap: string;
  nombre: string;
  molecula: string;
  precio_vvf: number;
  distribuidor: string;
  inafecto_devolucion: boolean;
  descripcion?: string;
  stock?: number;
}

export interface ProductoInventario {
  codigo_sap: string;
  stock: number;
  lote: string;
}
