import { useCallback, useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fetchMe, login as apiLogin, logout as apiLogout } from "../../services/api/auth";
import { setAuthLostHandler, tokens } from "../../services/api/client";
import { AuthContext, makeHasRole } from "./auth-context";

export default function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(tokens.access));

  useEffect(() => {
    setAuthLostHandler(() => { setUser(null); queryClient.clear(); });   // called when a token refresh fails
    if (!tokens.access) return;
    fetchMe()
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setLoading(false));
  }, [queryClient]);

  const login = useCallback(async (username, password) => {
    const me = await apiLogin(username, password);
    queryClient.clear();                       // nothing from a previous user may be reused
    setUser(me);
    return me;
  }, [queryClient]);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    queryClient.clear();                       // the next person to sign in starts with an empty cache
  }, [queryClient]);

  const value = useMemo(() => ({
    user, loading, login, logout,
    isSuperAdmin: user?.roles?.includes("super_admin") ?? false,
    hasRole: makeHasRole(user),
  }), [user, loading, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}