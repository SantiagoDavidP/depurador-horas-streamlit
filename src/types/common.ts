export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  key: string;
  direction: SortDirection;
}

export interface FilterConfig {
  search?: string;
  estado?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_direction?: SortDirection;
}

export interface SelectOption {
  value: string;
  label: string;
}

export type CondicionPago = 'Contado' | 'Credito 30 dias' | 'Credito 60 dias';

export const CONDICIONES_PAGO: SelectOption[] = [
  { value: 'Contado', label: 'Contado' },
  { value: 'Credito 30 dias', label: 'Credito 30 dias' },
  { value: 'Credito 60 dias', label: 'Credito 60 dias' },
];

export const RAZONES_DEVOLUCION: SelectOption[] = [
  { value: 'Producto dañado', label: 'Producto danado' },
  { value: 'Fecha de vencimiento proxima', label: 'Fecha de vencimiento proxima' },
  { value: 'Error en el pedido', label: 'Error en el pedido' },
  { value: 'Cliente rechazo entrega', label: 'Cliente rechazo entrega' },
  { value: 'Defecto de fabricacion', label: 'Defecto de fabricacion' },
];
