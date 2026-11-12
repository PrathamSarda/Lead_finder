import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "../components/layout/Layout";
import ProtectedRoute from "../components/auth/ProtectedRoute";
import Login from "../pages/Login";
import Settings from "../pages/Settings";
import NotFound from "../pages/NotFound";
import Dashboard from "../pages/Dashboard";

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<Login />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
