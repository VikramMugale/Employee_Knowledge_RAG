import React, { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function Layout() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  function signOut() {
    logout();
    navigate("/login", { replace: true });
  }

  const initial = (user.full_name || user.email || "U").slice(0, 1).toUpperCase();

  return (
    <div className="shell">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">
          <span className="brand-mark">AK</span>
          <div>
            <strong>Acme Knowledge</strong>
            <p>{isAdmin ? "Admin workspace" : "Employee assistant"}</p>
          </div>
        </div>

        <nav onClick={() => setMenuOpen(false)}>
          <NavLink to="/ask">
            <span>Ask</span>
            <small>Policy questions</small>
          </NavLink>
          {isAdmin && (
            <>
              <NavLink to="/policies">
                <span>Policies</span>
                <small>Indexed sources</small>
              </NavLink>
              <NavLink to="/admin">
                <span>Dashboard</span>
                <small>Index and quality</small>
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar-user">
          <div className="user-row">
            <div className="avatar">{initial}</div>
            <div>
              <strong>{user.full_name || user.email}</strong>
              <p>
                <span className={`role-pill ${isAdmin ? "admin" : ""}`}>{user.role}</span>
                {user.department ? ` · ${user.department}` : ""}
              </p>
            </div>
          </div>
          <button type="button" className="linkish" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <button type="button" className="menu-btn" onClick={() => setMenuOpen((open) => !open)}>
            Menu
          </button>
          <p className="topbar-note">
            {isAdmin
              ? "You can seed the index, inspect quality, and chat."
              : "You can ask policy questions. Management tools are admin-only."}
          </p>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
