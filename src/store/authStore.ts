import { create } from 'zustand';
import type { User, LoginCredentials } from '@/types';
import { authService } from '@/services';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  loginMicrosoft: () => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: authService.getStoredUser(),
  token: authService.getToken(),
  isLoading: false,
  error: null,
  isAuthenticated: authService.isAuthenticated(),

  login: async (credentials: LoginCredentials) => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.login(credentials);
      set({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al iniciar sesion';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  loginMicrosoft: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await authService.loginMicrosoft();
      set({
        user: response.user,
        token: response.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error con Microsoft SSO';
      set({ error: message, isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    try {
      await authService.logout();
    } finally {
      set({
        user: null,
        token: null,
        isAuthenticated: false,
        error: null,
      });
    }
  },

  loadUser: () => {
    const user = authService.getStoredUser();
    const token = authService.getToken();
    set({
      user,
      token,
      isAuthenticated: Boolean(token && user),
    });
  },

  clearError: () => set({ error: null }),
}));
