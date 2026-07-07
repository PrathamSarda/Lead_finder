import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { authApi } from "../api/auth";
import { tokenStorage } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const bootstrap = async () => {
      const token = tokenStorage.getAccessToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await authApi.me();
        setUser(currentUser);
      } catch {
        tokenStorage.clearTokens();
      } finally {
        setIsLoading(false);
      }
    };
    bootstrap();
  }, []);

  const login = async (credentials) => {
    const data = await authApi.login(credentials);
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    const currentUser = await authApi.me();
    setUser(currentUser);
    return currentUser;
  };

  const logout = () => {
    tokenStorage.clearTokens();
    setUser(null);
  };

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      logout,
    }),
    [user, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
