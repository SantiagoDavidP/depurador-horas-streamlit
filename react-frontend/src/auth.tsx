import React, { PropsWithChildren, useMemo } from "react";
import {
  MsalProvider,
  useIsAuthenticated,
  useMsal,
} from "@azure/msal-react";
import { InteractionRequiredAuthError, PublicClientApplication } from "@azure/msal-browser";

export const authEnabled =
  String(import.meta.env.VITE_AZURE_AD_ENABLED || "false").toLowerCase() === "true";

const clientId = import.meta.env.VITE_AZURE_AD_CLIENT_ID || "";
const tenantId = import.meta.env.VITE_AZURE_AD_TENANT_ID || "";
const redirectUri = import.meta.env.VITE_AZURE_AD_REDIRECT_URI || window.location.origin;

export const msalInstance = new PublicClientApplication({
  auth: {
    clientId,
    authority: tenantId ? `https://login.microsoftonline.com/${tenantId}` : undefined,
    redirectUri,
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
  },
});

export const scopes = ["User.Read", "GroupMember.Read.All"];

export const getAccessToken = async (): Promise<string | null> => {
  if (!authEnabled) return null;
  const account =
    msalInstance.getActiveAccount() || msalInstance.getAllAccounts()[0];
  if (!account) return null;
  try {
    const result = await msalInstance.acquireTokenSilent({ account, scopes });
    return result.accessToken;
  } catch (err) {
    if (err instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect({ scopes });
    }
    return null;
  }
};

export const AuthProvider = ({ children }: PropsWithChildren) => {
  if (!authEnabled) {
    return <>{children}</>;
  }
  return <MsalProvider instance={msalInstance}>{children}</MsalProvider>;
};

export const useAuthToken = () => {
  const msal = useMsal();
  const isAuthenticated = useIsAuthenticated();

  return useMemo(async () => {
    if (!authEnabled) return null;
    if (!isAuthenticated) return null;
    const account = msal.instance.getActiveAccount() || msal.instance.getAllAccounts()[0];
    if (!account) return null;

    try {
      const result = await msal.instance.acquireTokenSilent({ account, scopes });
      return result.accessToken;
    } catch (err) {
      if (err instanceof InteractionRequiredAuthError) {
        await msal.instance.acquireTokenRedirect({ scopes });
      }
      return null;
    }
  }, [isAuthenticated, msal.instance]);
};

const MsalGate = ({ children }: PropsWithChildren) => {
  const isAuthenticated = useIsAuthenticated();
  const msal = useMsal();

  if (!isAuthenticated) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h1>Autenticacion requerida</h1>
          <p>Esta aplicacion requiere iniciar sesion con tu cuenta Microsoft.</p>
          <button
            className="button primary full"
            onClick={() => msal.instance.loginRedirect({ scopes })}
          >
            Iniciar sesion con Microsoft
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export const AuthGate = ({ children }: PropsWithChildren) => {
  if (!authEnabled) {
    return <>{children}</>;
  }
  return <MsalGate>{children}</MsalGate>;
};
