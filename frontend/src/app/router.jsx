import { createBrowserRouter, Navigate } from "react-router-dom";
import { Guard, RequireAuth } from "./guards";
import { EXTRA_ROUTES, SCREENS } from "./screens";
import AppLayout from "../components/layout/AppLayout";
import LoginPage from "../features/auth/LoginPage";
import NotFound from "../components/common/NotFound";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [{
      element: <AppLayout />,
      children: [
        { index: true, element: <Navigate to="/dashboard" replace /> },
        ...[...SCREENS, ...EXTRA_ROUTES].map((s) => ({
          path: s.path,
          element: <Guard roles={s.roles}>{s.element}</Guard>,
        })),
        { path: "*", element: <NotFound /> },
      ],
    }],
  },
]);