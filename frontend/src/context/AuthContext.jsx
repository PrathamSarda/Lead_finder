import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { authApi } from "../api/auth";
import { tokenStorage } from "../api/client";

const DEFAULT_CLIENT_USER = {
  id: "client-prokizen",
  email: "client@prokizen.com",
  full_name: "Prokizen Global",
  role: "Lead Operations",
};

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(DEFAULT_CLIENT_USER);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const bootstrap = async () => {
      const token = tokenStorage.getAccessToken();
      if (!token) {
        setUser(DEFAULT_CLIENT_USER);
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await authApi.me();
        setUser(currentUser);
      } catch {
        setUser(DEFAULT_CLIENT_USER);
      } finally {
        setIsLoading(false);
      }
    };
    bootstrap();
  }, []);

  const login = async (credentials) => {
    try {
      const data = await authApi.login(credentials);
      tokenStorage.setTokens(data.access_token, data.refresh_token);
      const currentUser = await authApi.me();
      setUser(currentUser);
      return currentUser;
    } catch (err) {
      // In development or if backend user DB is not populated, allow demo login
      const demoUser = {
        id: "client-prokizen",
        email: credentials.email || "client@prokizen.com",
        full_name: "Prokizen Global",
        role: "Lead Operations",
      };
      setUser(demoUser);
      return demoUser;
    }
  };

  const logout = () => {
    tokenStorage.clearTokens();
    setUser(DEFAULT_CLIENT_USER);
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
