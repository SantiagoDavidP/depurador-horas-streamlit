import React from 'react';
import { Navigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Activity, Mail, Lock, LogIn } from 'lucide-react';
import { useAuth } from '@/hooks';
import { Button } from '@/components/common';

const loginSchema = z.object({
  email: z.string().email('Ingrese un correo valido'),
  password: z.string().min(1, 'La contrasena es obligatoria'),
  remember: z.boolean().optional(),
});

type LoginFormData = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { isAuthenticated, isLoading, login, loginMicrosoft } = useAuth();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', remember: false },
  });

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  const onSubmit = async (data: LoginFormData) => {
    await login({
      email: data.email,
      password: data.password,
      remember: data.remember,
    });
  };

  return (
    <div className="bg-gradient-to-br from-blue-50 via-white to-blue-50 min-h-screen flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-700 rounded-2xl mb-4 shadow-lg shadow-blue-200">
            <Activity className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-slate-900">BONAPHARM</h1>
          <p className="text-slate-600 text-sm mt-2">
            Sistema de Pedidos y Devoluciones
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
          <h2 className="text-xl font-semibold text-slate-900 mb-6">
            Iniciar Sesion
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-slate-700 mb-2"
              >
                Correo Electronico
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  id="email"
                  type="email"
                  placeholder="usuario@bonapharm.com"
                  {...register('email')}
                  className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20 focus:border-blue-700 transition-colors"
                />
              </div>
              {errors.email && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-slate-700"
                >
                  Contrasena
                </label>
                <a
                  href="#recuperar"
                  className="text-xs text-blue-700 hover:text-blue-800 cursor-pointer transition-colors"
                >
                  Olvidaste tu contrasena?
                </a>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  id="password"
                  type="password"
                  placeholder="Ingrese contrasena"
                  {...register('password')}
                  className="w-full pl-11 pr-4 py-3 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-700/20 focus:border-blue-700 transition-colors"
                />
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* Remember */}
            <div className="flex items-center">
              <input
                id="remember"
                type="checkbox"
                {...register('remember')}
                className="w-4 h-4 text-blue-700 border-slate-300 rounded focus:ring-2 focus:ring-blue-700/20 cursor-pointer"
              />
              <label
                htmlFor="remember"
                className="ml-2 text-sm text-slate-600 cursor-pointer"
              >
                Recordar mi sesion
              </label>
            </div>

            {/* Submit */}
            <Button
              type="submit"
              isLoading={isLoading}
              leftIcon={<LogIn className="w-5 h-5" />}
              className="w-full py-3"
            >
              Iniciar Sesion
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white px-3 text-slate-500">
                O continuar con
              </span>
            </div>
          </div>

          {/* Microsoft SSO */}
          <button
            type="button"
            onClick={loginMicrosoft}
            className="w-full flex items-center justify-center gap-3 border border-slate-300 py-3 rounded-lg font-medium text-sm text-slate-700 hover:bg-slate-50 cursor-pointer transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 23 23" fill="none">
              <path d="M0 0h11v11H0V0z" fill="#F25022" />
              <path d="M12 0h11v11H12V0z" fill="#7FBA00" />
              <path d="M0 12h11v11H0V12z" fill="#00A4EF" />
              <path d="M12 12h11v11H12V12z" fill="#FFB900" />
            </svg>
            Microsoft Entra ID
          </button>

          <p className="text-center text-xs text-slate-500 mt-6">
            Acceso exclusivo para personal autorizado de BONAPHARM.
            <br />
            <a
              href="#soporte"
              className="text-blue-700 hover:underline cursor-pointer"
            >
              Contactar soporte tecnico
            </a>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-6">
          BONAPHARM DEL PERU. Todos los derechos reservados.
          <br />
          Protegido por Azure AD - TLS 1.2+ - AES-256
        </p>
      </div>
    </div>
  );
};
