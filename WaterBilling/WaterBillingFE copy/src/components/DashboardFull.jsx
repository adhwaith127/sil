import React, { useEffect, useState } from "react";
import "../styles/DashboardFull.css";


export default function DashboardFull() {
  const [liveUsers, setLiveUsers] = useState(0);
  const [totalCollection, setTotalCollection] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setLiveUsers(Math.floor(Math.random() * 500) + 50);
      setTotalCollection(Math.floor(Math.random() * 10000) + 1000);
    }, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="dashboard" role="region" aria-label="Dashboard">
      <div className="dashboard__header">
        <h1 className="dashboard__title">Water Billing</h1>
      </div>

      <div className="dashboard__cards" role="list">
        <div className="dashboard__card" role="listitem" aria-label="Live users">
          <h3 className="dashboard__card-title">Live User Status</h3>
          <div className="dashboard__value">{liveUsers}</div>
          <div className="dashboard__muted">Active users right now</div>
        </div>

        <div className="dashboard__card" role="listitem" aria-label="Total collection">
          <h3 className="dashboard__card-title">Total Collection</h3>
          <div className="dashboard__value">₹{totalCollection}</div>
          <div className="dashboard__muted">Amount collected today</div>
        </div>

        <div className="dashboard__card" role="listitem" aria-label="Quick actions">
          <h3 className="dashboard__card-title">Quick Actions</h3>
          <div className="dashboard__muted">Use the top navigation to open modules: Consumers, Devices, Reports.</div>
        </div>
      </div>
    </div>
  );
}
