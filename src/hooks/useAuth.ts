import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store';
import { useNotificationStore } from '@/store';
import type { LoginCredentials, UserRole } from '@/types';

export function useAuth() {
  const navigate = useNavigate();
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    login: storeLogin,
    loginMicrosoft: storeLoginMicrosoft,
    logout: storeLogout,
    clearError,
  } = useAuthStore();
  const addToast = useNotificationStore((s) => s.addToast);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      try {
        await storeLogin(credentials);
        addToast({ type: 'success', title: 'Bienvenido', message: 'Sesion iniciada correctamente' });
        navigate('/dashboard');
      } catch {
        addToast({ type: 'error', title: 'Error de autenticacion', message: 'Credenciales incorrectas' });
      }
    },
    [storeLogin, navigate, addToast]
  );

  const loginMicrosoft = useCallback(async () => {
    try {
      await storeLoginMicrosoft();
      addToast({ type: 'success', title: 'Bienvenido', message: 'Sesion iniciada con Microsoft' });
      navigate('/dashboard');
    } catch {
      addToast({ type: 'error', title: 'Error SSO', message: 'No se pudo autenticar con Microsoft' });
    }
  }, [storeLoginMicrosoft, navigate, addToast]);

  const logout = useCallback(async () => {
    await storeLogout();
    navigate('/login');
  }, [storeLogout, navigate]);

  const hasRole = useCallback(
    (roles: UserRole[]): boolean => {
      if (!user) return false;
      return roles.includes(user.rol);
    },
    [user]
  );

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    loginMicrosoft,
    logout,
    hasRole,
    clearError,
  };
}
