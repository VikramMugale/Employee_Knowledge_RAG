import React from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth/AuthContext.jsx";
import Layout from "./components/Layout.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";
import DocumentsPage from "./pages/DocumentsPage.jsx";
import AdminPage from "./pages/AdminPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";

function Splash() {
  return (
    <div className="boot">
      <div className="boot-card">
        <span className="brand-mark">AK</span>
        <p>Opening your workspace…</p>
      </div>
    </div>
  );
}

function Protected({ children }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <Splash />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}

function GuestOnly({ children }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <Splash />;
  if (user) {
    const next = location.state?.from && location.state.from !== "/login" ? location.state.from : "/ask";
    return <Navigate to={next} replace />;
  }
  return children;
}

function AdminOnly({ children }) {
  const { ready, user, isAdmin } = useAuth();
  const location = useLocation();
  if (!ready) return <Splash />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!isAdmin) return <Navigate to="/ask" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        }
      />
      <Route
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route path="/" element={<Navigate to="/ask" replace />} />
        <Route path="/ask" element={<ChatPage />} />
        <Route
          path="/policies"
          element={
            <AdminOnly>
              <DocumentsPage />
            </AdminOnly>
          }
        />
        <Route path="/documents" element={<Navigate to="/policies" replace />} />
        <Route
          path="/admin"
          element={
            <AdminOnly>
              <AdminPage />
            </AdminOnly>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
