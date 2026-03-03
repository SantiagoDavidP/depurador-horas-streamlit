import { IAuthRepository } from "../domain/IAuthRepository";
import { AuthUser } from "../domain/AuthUser";
import { msalInstance, scopes } from "./MsalConfig";
import { InteractionRequiredAuthError } from "@azure/msal-browser";

export class AuthRepositoryImpl implements IAuthRepository {

  async login(): Promise<void> {
    await msalInstance.loginRedirect({ scopes });
  }

  async logout(): Promise<void> {
    await msalInstance.logoutRedirect();
  }

  isAuthenticated(): boolean {
    return msalInstance.getAllAccounts().length > 0;
  }

  async getAccessToken(): Promise<string | null> {
    const account = msalInstance.getActiveAccount() || msalInstance.getAllAccounts()[0];
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
  }

  async getCurrentUser(): Promise<AuthUser | null> {
    const account = msalInstance.getActiveAccount() || msalInstance.getAllAccounts()[0];
    if (!account) return null;

    return {
      id: account.localAccountId,
      name: account.name || "",
      email: account.username,
    };
  }
}