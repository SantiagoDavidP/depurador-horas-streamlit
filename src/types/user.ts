export type UserRole = 'vendedor' | 'admin_comercial' | 'finanzas' | 'gerente';

export interface User {
  id: string;
  email: string;
  nombre: string;
  apellido: string;
  rol: UserRole;
  avatar_url?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember?: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  vendedor: 'Vendedor',
  admin_comercial: 'Admin Comercial',
  finanzas: 'Finanzas',
  gerente: 'Gerente General',
};

export function getUserInitials(user: User): string {
  return `${user.nombre.charAt(0)}${user.apellido.charAt(0)}`.toUpperCase();
}

export function getRoleGradient(rol: UserRole): string {
  const gradients: Record<UserRole, string> = {
    vendedor: 'from-blue-600 to-sky-500',
    admin_comercial: 'from-green-500 to-emerald-600',
    finanzas: 'from-purple-500 to-indigo-600',
    gerente: 'from-orange-500 to-red-600',
  };
  return gradients[rol];
}
