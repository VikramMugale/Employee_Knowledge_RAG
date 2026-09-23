import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  clearSession,
  fetchMe,
  getStoredUser,
  getToken,
  login as loginRequest,
  storeSession,
} from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser());
  const [ready, setReady] = useState(false);

  function endSession() {
    clearSession();
    setUser(null);
  }

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setReady(true);
      return;
    }
    fetchMe()
      .then((profile) => {
        setUser(profile);
        storeSession(token, profile);
      })
      .catch(() => endSession())
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    const onExpired = () => endSession();
    window.addEventListener("rag:unauthorized", onExpired);
    return () => window.removeEventListener("rag:unauthorized", onExpired);
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      isAdmin: user?.role === "ADMIN",
      async login(email, password) {
        const session = await loginRequest(email, password);
        storeSession(session.access_token, session.user);
        setUser(session.user);
        return session.user;
      },
      logout: endSession,
    }),
    [user, ready]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
