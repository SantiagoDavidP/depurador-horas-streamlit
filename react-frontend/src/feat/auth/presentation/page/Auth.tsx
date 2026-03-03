import React, { PropsWithChildren } from "react";
import { MsalProvider } from "@azure/msal-react";
import { useAuthViewModel } from "../view_model/AuthViewModel";
import { msalInstance, authEnabled } from "../../data/MsalConfig";
import { Button } from "../../../../core/ui/design/atoms/Button";
import { Typography } from "../../../../core/ui/design/atoms/Typography";

export const AuthProvider: React.FC<PropsWithChildren> = ({ children }) => {
  if (!authEnabled) {
    return <>{children}</>;
  }
  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
};

export const AuthGate: React.FC<PropsWithChildren> = ({ children }) => {
  const { isAuthenticated, login, loading } = useAuthViewModel();

  if (!authEnabled) {
    return <>{children}</>;
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <Typography variant="h3">Cargando...</Typography>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <Typography variant="h1">Autenticación requerida</Typography>
          <p>Esta aplicación requiere iniciar sesión con tu cuenta Microsoft.</p>
          <Button
            variant="primary"
            fullWidth
            onClick={login}
          >
            Iniciar sesión con Microsoft
          </Button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export const AuthPage = () => {
  const { user, login, logout, isAuthenticated, loading } = useAuthViewModel();

  if (loading) return <div>Cargando...</div>;

  if (!isAuthenticated) {
    return (
      <div>
        <Typography variant="h1">Autenticación requerida</Typography>
        <Button onClick={login}>Iniciar sesión</Button>
      </div>
    );
  }

  return (
    <div>
      <Typography variant="h1">Bienvenido {user?.name}</Typography>
      <Button onClick={logout}>Cerrar sesión</Button>
    </div>
  );
};