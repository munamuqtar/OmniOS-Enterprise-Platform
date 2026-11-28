import { createContext, useContext } from "react";

export const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

/** Super Admin passes every role check. hasRole() with no roles means "Super Admin only". */
export const makeHasRole = (user) => (...roles) =>
  !!user && (user.roles.includes("super_admin") || roles.some((r) => user.roles.includes(r)));