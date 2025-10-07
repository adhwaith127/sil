import React, { useState } from "react";
import "../styles/DeviceDetails.css";

export default function DeviceDetailsManager() {
  const [form, setForm] = useState({ deviceId: "", deviceMachId: "" });
  const [rows, setRows] = useState([
    { id: 1, deviceId: "1", deviceMachId: "202008AMP065237B" },
  ]);
  const [query, setQuery] = useState("");

  const onChange = (field) => (e) => setForm((s) => ({ ...s, [field]: e.target.value }));

  function handleSave() {
    const id = form.deviceId.trim();
    const mach = form.deviceMachId.trim();
    if (!id || !mach) return alert("Enter both Device ID and Device Mach ID.");
    setRows((prev) => {
      const exists = prev.findIndex((r) => r.deviceId === id);
      if (exists >= 0) return prev.map((r, i) => (i === exists ? { ...r, deviceMachId: mach } : r));
      return [...prev, { id: prev.length + 1, deviceId: id, deviceMachId: mach }];
    });
    setForm({ deviceId: "", deviceMachId: "" });
    setQuery("");
  }

  function handleDelete() {
    const id = form.deviceId.trim();
    if (!id) return alert("Enter Device ID to delete");
    setRows((prev) => prev.filter((r) => r.deviceId !== id));
    setForm({ deviceId: "", deviceMachId: "" });
  }

  function handleClear() {
    setForm({ deviceId: "", deviceMachId: "" });
    setQuery("");
  }

  function handleSearch() {
    setQuery(form.deviceMachId.trim().toLowerCase());
  }

  function handleRowClick(r) {
    setForm({ deviceId: r.deviceId, deviceMachId: r.deviceMachId });
  }

  const visible = query ? rows.filter((r) => r.deviceMachId.toLowerCase().includes(query)) : rows;

  return (
    <div className="device-details">
      <div className="device-details__card" role="region" aria-label="Device details">
        <h2 className="device-details__title">DEVICE DETAILS</h2>

        <div className="device-details__form">
          <label>
            <div className="device-details__label">Device ID</div>
            <input className="device-details__input" value={form.deviceId} onChange={onChange("deviceId")} placeholder="Device ID" />
          </label>

          <label>
            <div className="device-details__label">Device Mach ID</div>
            <input className="device-details__input" value={form.deviceMachId} onChange={onChange("deviceMachId")} placeholder="Machine ID" />
          </label>
        </div>

        <div className="device-details__actions">
          <button onClick={handleDelete} className="device-details__btn">Delete</button>
          <button onClick={handleClear} className="device-details__btn">Clear</button>
          <button onClick={handleSearch} className="device-details__btn">Search</button>
          <button onClick={handleSave} className="device-details__btn device-details__btn--primary">Save</button>
        </div>

        <table className="device-details__table" aria-label="device list">
          <thead>
            <tr>
              <th>SL No.</th>
              <th>Device ID</th>
              <th>Device Mach ID</th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr><td colSpan="3">No records</td></tr>
            ) : (
              visible.map((r, i) => (
                <tr key={r.deviceId} onClick={() => handleRowClick(r)}>
                  <td>{i + 1}</td>
                  <td>{r.deviceId}</td>
                  <td>{r.deviceMachId}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
