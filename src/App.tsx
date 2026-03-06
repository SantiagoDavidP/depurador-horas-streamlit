import React from 'react';
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
  Outlet,
} from 'react-router-dom';
import { AppLayout } from '@/components/layout';
import { ToastContainer } from '@/components/common';
import { useAuthStore } from '@/store';
import {
  LoginPage,
  DashboardVendedorPage,
  RegistroPedidosPage,
  ConsultaPedidosPage,
  AprobacionPedidosPage,
  GestionDevolucionesPage,
  CalculoComisionesPage,
  PowerBIReportsPage,
} from '@/pages';

const ProtectedRoute: React.FC = () => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <Outlet />;
};

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: '/dashboard',
            element: <DashboardVendedorPage />,
          },
          {
            path: '/pedidos/nuevo',
            element: <RegistroPedidosPage />,
          },
          {
            path: '/pedidos',
            element: <ConsultaPedidosPage />,
          },
          {
            path: '/pedidos/aprobacion',
            element: <AprobacionPedidosPage />,
          },
          {
            path: '/devoluciones',
            element: <GestionDevolucionesPage />,
          },
          {
            path: '/comisiones',
            element: <CalculoComisionesPage />,
          },
          {
            path: '/reportes',
            element: <PowerBIReportsPage />,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/login" replace />,
  },
]);

const App: React.FC = () => {
  return (
    <>
      <RouterProvider router={router} />
      <ToastContainer />
    </>
  );
};

export default App;
