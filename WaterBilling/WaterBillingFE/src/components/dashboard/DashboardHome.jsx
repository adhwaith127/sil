import React, { useState, useEffect } from "react";

export default function DashboardHome() {
  const [liveUsers, setLiveUsers] = useState(0);
  const [totalCollection, setTotalCollection] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setLiveUsers(Math.floor(Math.random() * 500) + 50);
      setTotalCollection(Math.floor(Math.random() * 10000) + 1000);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="dashboard-center">
      <h1 style={{ margin: 0 }}>Water Billing</h1>
      <div className="status-cards">
        <div className="card">
          <h3>Live User Status</h3>
          <div style={{ fontSize: 28, fontWeight: 800 }}>{liveUsers}</div>
          <div className="small-muted">Active users online now</div>
        </div>

        <div className="card">
          <h3>Total Collection</h3>
          <div style={{ fontSize: 28, fontWeight: 800 }}>${totalCollection}</div>
          <div className="small-muted">Amount collected today</div>
        </div>
      </div>
    </div>
  );
}