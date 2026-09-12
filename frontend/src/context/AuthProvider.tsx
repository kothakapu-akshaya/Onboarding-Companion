import { useEffect, useState, type ReactNode } from "react";

import { login as apiLogin, getCurrentUser } from "../services/auth";

import { AuthContext, type AuthStatus } from "./auth";
import type { UserProfile } from "../types/user";

const TOKEN_KEY = "token";

function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    let active = true;

    const restoreSession = async () => {
      const token = localStorage.getItem(TOKEN_KEY);

      if (!token) {
        if (active) setStatus("unauthenticated");
        return;
      }

      try {
        const profile = await getCurrentUser();
        if (active) {
          setUser(profile);
          setStatus("authenticated");
        }
      } catch (error) {
        console.error("Session restore failed", error);
        localStorage.removeItem(TOKEN_KEY);
        if (active) setStatus("unauthenticated");
      }
    };

    restoreSession();

    return () => {
      active = false;
    };
  }, []);

  const login = async (phone: string, password: string) => {
    const data = await apiLogin(phone, password);

    if (data.access_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
    }

    const profile = await getCurrentUser();

    setUser(profile);
    setStatus("authenticated");
  };

  const logout = () => {
    // Only clear authentication state. Server-side onboarding data and any
    // retained local onboarding-progress are intentionally left untouched.
    localStorage.removeItem(TOKEN_KEY);

    setUser(null);
    setStatus("unauthenticated");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        isAuthenticated: status === "authenticated",
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export default AuthProvider;
