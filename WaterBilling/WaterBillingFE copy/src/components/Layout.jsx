import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import "../styles/Layout.css";

export default function Layout() {
  const linkClass = ({ isActive }) =>
    `layout__link ${isActive ? "layout__link--active" : ""}`;

  return (
    <div className="layout">
      <header className="layout__header">
        <div className="layout__brand">WaterBillingFE</div>

        <nav className="layout__nav" aria-label="Main navigation">
          <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
          <NavLink to="/register" className={linkClass}>Register</NavLink>
          <NavLink to="/devices" className={linkClass}>Devices</NavLink>
          <NavLink to="/device-setup" className={linkClass}>Device Setup</NavLink>
          <NavLink to="/consumers" className={linkClass}>Consumers</NavLink>
          <NavLink to="/consumer-types" className={linkClass}>Consumer Types</NavLink>
          <NavLink to="/reports" className={linkClass}>Reports</NavLink>
        </nav>

        <div className="layout__spacer" />

        <div className="layout__status" aria-hidden>
          <div>v1.0</div>
        </div>
      </header>

      <main className="layout__main">
        <Outlet />
      </main>

      <footer className="layout__footer">
        © {new Date().getFullYear()} Water Billing — Frontend
      </footer>
    </div>
  );
}