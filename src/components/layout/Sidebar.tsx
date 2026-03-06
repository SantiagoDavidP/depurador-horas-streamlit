import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  LayoutDashboard,
  ShoppingCart,
  ClipboardList,
  CheckCircle,
  PackageX,
  Percent,
  BarChart3,
  LogOut,
  X,
} from 'lucide-react';
import { cn } from '@/utils';
import { useAuthStore } from '@/store';
import { getUserInitials, getRoleGradient, ROLE_LABELS } from '@/types/user';
import type { UserRole } from '@/types';

interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  roles: UserRole[];
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const sections: NavSection[] = [
  {
    title: '',
    items: [
      {
        to: '/dashboard',
        label: 'Dashboard',
        icon: <LayoutDashboard className="w-5 h-5" />,
        roles: ['vendedor', 'admin_comercial', 'finanzas', 'gerente'],
      },
    ],
  },
  {
    title: 'Portal Vendedor',
    items: [
      {
        to: '/pedidos/nuevo',
        label: 'Registro de Pedidos',
        icon: <ShoppingCart className="w-5 h-5" />,
        roles: ['vendedor', 'admin_comercial', 'gerente'],
      },
      {
        to: '/pedidos',
        label: 'Consulta de Pedidos',
        icon: <ClipboardList className="w-5 h-5" />,
        roles: ['vendedor', 'admin_comercial', 'gerente'],
      },
    ],
  },
  {
    title: 'Portal Distribuidor',
    items: [
      {
        to: '/pedidos/aprobacion',
        label: 'Aprobacion de Pedidos',
        icon: <CheckCircle className="w-5 h-5" />,
        roles: ['admin_comercial', 'gerente'],
      },
      {
        to: '/devoluciones',
        label: 'Gestion Devoluciones',
        icon: <PackageX className="w-5 h-5" />,
        roles: ['admin_comercial', 'gerente'],
      },
      {
        to: '/comisiones',
        label: 'Calculo Comisiones',
        icon: <Percent className="w-5 h-5" />,
        roles: ['finanzas', 'gerente'],
      },
    ],
  },
  {
    title: 'Reportes',
    items: [
      {
        to: '/reportes',
        label: 'Power BI Reports',
        icon: <BarChart3 className="w-5 h-5" />,
        roles: ['vendedor', 'admin_comercial', 'finanzas', 'gerente'],
      },
    ],
  },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const filteredSections = sections
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) => !user || item.roles.includes(user.rol)
      ),
    }))
    .filter((section) => section.items.length > 0);

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200 flex flex-col flex-shrink-0 transform transition-transform duration-200',
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-700 rounded-lg flex items-center justify-center">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-slate-900">BONAPHARM</span>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1 text-slate-400 hover:text-slate-600 cursor-pointer"
            aria-label="Cerrar menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-1 overflow-y-auto">
          {filteredSections.map((section, idx) => (
            <div key={idx}>
              {section.title && (
                <div className="pt-4 pb-2 px-3">
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    {section.title}
                  </p>
                </div>
              )}
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors duration-150',
                      isActive
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-slate-600 hover:bg-slate-100'
                    )
                  }
                >
                  {item.icon}
                  <span className="text-sm">{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {user && (
          <div className="border-t border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  'w-10 h-10 rounded-full bg-gradient-to-br flex items-center justify-center text-white text-sm font-semibold',
                  getRoleGradient(user.rol)
                )}
              >
                {getUserInitials(user)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-900 truncate">
                  {user.nombre} {user.apellido}
                </p>
                <p className="text-xs text-slate-500 truncate">
                  {ROLE_LABELS[user.rol]}
                </p>
              </div>
              <button
                onClick={() => { logout(); }}
                className="text-slate-400 hover:text-slate-600 cursor-pointer transition-colors"
                aria-label="Cerrar sesion"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
