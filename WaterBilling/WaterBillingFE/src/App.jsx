import React, { useEffect, useState, useRef } from "react";
import { Outlet, useNavigate } from "react-router-dom";

// Global CSS - injected once
const GLOBAL_CSS = `
:root{ --bg:#f6fbff; --card:#fff; --accent:#2563eb; --muted:#475569; }
*{box-sizing:border-box}
body{ margin:0; font-family:Inter, Roboto, Arial, sans-serif; background:#f3f6fb; }
.app-header{ background: linear-gradient(90deg,#2563eb,#1e40af); color:white; padding:12px 18px; display:flex; align-items:center; justify-content:space-between; }
.header-left{ display:flex; align-items:center; gap:12px; }
.app-title{ font-weight:700; font-size:18px; cursor:pointer; }
.nav{ display:flex; gap:12px; align-items:center; }
.nav-button{ background:transparent; border:none; color:white; cursor:pointer; padding:8px 10px; border-radius:6px; font-weight:600; }
.nav-button:hover{ background: rgba(255,255,255,0.06); }
.dropdown{ position:relative; }
.dropdown-menu{ position:absolute; top:38px; left:0; background:white; color:#0f172a; border-radius:8px; box-shadow:0 8px 24px rgba(2,6,23,0.12); min-width:180px; padding:6px; z-index:50; }
.dropdown-item{ padding:8px 10px; cursor:pointer; border-radius:6px; white-space:nowrap; }
.dropdown-item:hover{ background:#eef2ff; }
.container{ padding:20px; display:flex; align-items:flex-start; justify-content:center; }
.center-card{ width:100%; max-width:1100px; }
.dashboard-center{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; padding:36px; }
.status-cards{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; width:100%; }
.card{ background:white; border-radius:12px; padding:18px; box-shadow:0 6px 20px rgba(2,6,23,0.06); }
.card h3{ margin:0 0 8px 0; font-size:16px; }
.small-muted{ color:#64748b; font-size:13px; }
.form-grid{ display:grid; grid-template-columns:220px 1fr; gap:12px 16px; align-items:center; }
.input, select{ padding:9px 12px; border:1px solid #e6eef8; border-radius:8px; width:100%; }
.controls{ display:flex; gap:10px; margin-top:12px; align-items:center; }
.btn{ padding:8px 12px; border-radius:8px; border:1px solid #d0d7e6; background:white; cursor:pointer; font-weight:600; }
.btn.save{ margin-left:auto; background:var(--accent); color:white; border:none; }
.table{ width:100%; border-collapse:collapse; margin-top:12px; }
.table thead th{ text-align:left; padding:10px; background:#f8fbff; border-bottom:1px solid #eef3fb; }
.table tbody td{ padding:10px; border-top:1px solid #f3f7fb; }
.table tbody tr:hover{ background:#fbfdff; cursor:pointer; }
.sl{ width:64px; text-align:center; font-weight:700; background:#eef6ff; }
.hint{ color:#64748b; font-size:13px; margin-top:10px; }
@media (max-width:880px){ .form-grid{ grid-template-columns:1fr; } .header-left{ gap:8px; } }
`;

let _cssInjected = false;
const ensureCss = () => {
  if (_cssInjected) return;
  const style = document.createElement("style");
  style.textContent = GLOBAL_CSS;
  document.head.appendChild(style);
  _cssInjected = true;
};

export default function App() {
  ensureCss();
  const navigate = useNavigate();
  const [openDropdown, setOpenDropdown] = useState("");
  const rootRef = useRef(null);

  useEffect(() => {
    function onDoc(e) {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target)) setOpenDropdown("");
    }
    document.addEventListener("click", onDoc);
    return () => document.removeEventListener("click", onDoc);
  }, []);

  const goTo = (path) => {
    navigate(path);
    setOpenDropdown("");
  };

  return (
    <div ref={rootRef}>
      <header className="app-header">
        <div className="header-left">
          <div className="app-title" onClick={() => goTo("/")} role="button" tabIndex={0}>
            Dashboard
          </div>
        </div>

        <nav className="nav">
          <div className="dropdown">
            <button className="nav-button" onClick={() => setOpenDropdown((d) => (d === "company" ? "" : "company"))}>
              Company ▾
            </button>
            {openDropdown === "company" && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => goTo("/ward-details")}>Ward Details</div>
                <div className="dropdown-item" onClick={() => goTo("/general-settings")}>General Settings</div>
              </div>
            )}
          </div>

          <div className="dropdown">
            <button className="nav-button" onClick={() => setOpenDropdown((d) => (d === "user" ? "" : "user"))}>
              User ▾
            </button>
            {openDropdown === "user" && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => goTo("/mobile-user")}>Mobile User</div>
                <div className="dropdown-item" onClick={() => goTo("/web-user")}>Web User</div>
              </div>
            )}
          </div>

          <div className="dropdown">
            <button className="nav-button" onClick={() => setOpenDropdown((d) => (d === "tariff" ? "" : "tariff"))}>
              Tariff ▾
            </button>
            {openDropdown === "tariff" && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => goTo("/domestic-tariff")}>Domestic Tariff</div>
                <div className="dropdown-item" onClick={() => goTo("/meter-status")}>Meter Status</div>
              </div>
            )}
          </div>

          <div className="dropdown">
            <button className="nav-button" onClick={() => setOpenDropdown((d) => (d === "consumer" ? "" : "consumer"))}>
              Consumer ▾
            </button>
            {openDropdown === "consumer" && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => goTo("/consumer-type")}>Consumer Type</div>
                <div className="dropdown-item" onClick={() => goTo("/consumer-details")}>Consumer Details</div>
              </div>
            )}
          </div>

          <div className="dropdown">
            <button className="nav-button" onClick={() => setOpenDropdown((d) => (d === "device" ? "" : "device"))}>
              Device ▾
            </button>
            {openDropdown === "device" && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => goTo("/device-settings")}>Device Settings</div>
                <div className="dropdown-item" onClick={() => goTo("/device-details")}>Device Details</div>
              </div>
            )}
          </div>

          <div className="dropdown">
            <button className="nav-button" onClick={() => setOpenDropdown((d) => (d === "report" ? "" : "report"))}>
              Report ▾
            </button>
            {openDropdown === "report" && (
              <div className="dropdown-menu">
                <div className="dropdown-item" onClick={() => goTo("/consumer-report")}>Consumer Report</div>
                <div className="dropdown-item" onClick={() => goTo("/bill-report")}>Bill Report</div>
                <div className="dropdown-item" onClick={() => goTo("/payment-report")}>Payment Report</div>
              </div>
            )}
          </div>
        </nav>
      </header>

      <main className="container">
        <div className="center-card card" style={{ padding: 0 }}>
          <Outlet />
        </div>
      </main>
    </div>
  );
}