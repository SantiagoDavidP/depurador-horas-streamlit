import { AuthUser } from "./AuthUser";

export interface IAuthRepository {
  login(): Promise<void>;
  logout(): Promise<void>;
  getAccessToken(): Promise<string | null>;
  getCurrentUser(): Promise<AuthUser | null>;
  isAuthenticated(): boolean;
}