import { useEffect, useState } from "react";
import { AuthRepositoryImpl } from "../../data/AuthRepositoryImpl";
import { AuthUser } from "../../domain/AuthUser";

export const useAuthViewModel = () => {
  const repository = new AuthRepositoryImpl();

  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const loadUser = async () => {
    const currentUser = await repository.getCurrentUser();
    setUser(currentUser);
    setLoading(false);
  };

  const login = async () => {
    await repository.login();
  };

  const logout = async () => {
    await repository.logout();
  };

  useEffect(() => {
    loadUser();
  }, []);

  return {
    user,
    loading,
    login,
    logout,
    isAuthenticated: !!user,
  };
};