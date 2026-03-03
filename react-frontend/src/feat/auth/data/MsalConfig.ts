import { PublicClientApplication } from "@azure/msal-browser";

export const authEnabled = String(import.meta.env.VITE_AZURE_AD_ENABLED || "false").toLowerCase() === "true";

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