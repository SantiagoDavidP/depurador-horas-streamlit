import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  '/dashboard': { title: 'Dashboard General', subtitle: 'Resumen de actividad y metricas clave' },
  '/pedidos/nuevo': { title: 'Registro de Pedidos', subtitle: 'Crear nueva solicitud de pedido' },
  '/pedidos': { title: 'Consulta de Pedidos', subtitle: 'Historial y seguimiento de pedidos' },
  '/pedidos/aprobacion': { title: 'Aprobacion de Pedidos', subtitle: 'Revisar y aprobar solicitudes pendientes' },
  '/devoluciones': { title: 'Gestion de Devoluciones', subtitle: 'Registrar y aprobar solicitudes de devolucion' },
  '/comisiones': { title: 'Calculo de Comisiones', subtitle: 'Gestion automatica de comisiones por distribuidor' },
  '/reportes': { title: 'Reportes Gerenciales', subtitle: 'Analisis avanzado con Power BI' },
};

export const AppLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const pageInfo = pageTitles[location.pathname] ?? {
    title: 'BONAPHARM',
    subtitle: 'Sistema de Pedidos y Devoluciones',
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <main className="flex-1 flex flex-col overflow-hidden">
        <TopBar
          title={pageInfo.title}
          subtitle={pageInfo.subtitle}
          onMenuToggle={() => setSidebarOpen(true)}
        />

        <div className="flex-1 overflow-y-auto">
          <div className="p-6">
            <Outlet />
          </div>
        </div>
      </main>
    </div>
  );
};
