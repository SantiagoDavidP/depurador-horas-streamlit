import api from './api';
import type { AuthResponse, LoginCredentials, User, UserRole } from '@/types';

// Backend roles → frontend roles
const ROL_MAP: Record<string, UserRole> = {
  Vendedor: 'vendedor',
  AdminComercial: 'admin_comercial',
  Finanzas: 'finanzas',
  GerenteGeneral: 'gerente',
};

function mapBackendUser(me: { id: string; nombre_completo: string; email: string; rol: string }): User {
  const parts = me.nombre_completo.trim().split(' ');
  return {
    id: me.id,
    email: me.email,
    nombre: parts[0] ?? me.nombre_completo,
    apellido: parts.slice(1).join(' ') || '',
    rol: (ROL_MAP[me.rol] ?? 'vendedor') as UserRole,
  };
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // Step 1: obtener tokens
    const { data: tokenData } = await api.post<{ access_token: string; refresh_token: string }>('/api/auth/login', credentials);
    localStorage.setItem('access_token', tokenData.access_token);

    // Step 2: obtener datos del usuario con el token ya guardado
    const { data: meData } = await api.get<{ id: string; nombre_completo: string; email: string; rol: string }>('/api/auth/me');
    const user = mapBackendUser(meData);
    localStorage.setItem('user', JSON.stringify(user));

    return { access_token: tokenData.access_token, token_type: 'bearer', user };
  },

  async loginMicrosoft(): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/api/auth/login/microsoft');
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('user', JSON.stringify(data.user));
    return data;
  },

  async logout(): Promise<void> {
    try {
      await api.post('/api/auth/logout');
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
    }
  },

  async getCurrentUser(): Promise<User> {
    const { data } = await api.get<User>('/api/auth/me');
    return data;
  },

  getStoredUser(): User | null {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    try {
      return JSON.parse(raw) as User;
    } catch {
      return null;
    }
  },

  getToken(): string | null {
    return localStorage.getItem('access_token');
  },

  isAuthenticated(): boolean {
    return Boolean(this.getToken());
  },
};
