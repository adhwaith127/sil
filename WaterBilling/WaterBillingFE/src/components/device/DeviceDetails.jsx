import React, { useState } from "react";

export default function DeviceDetails() {
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
      if (exists >= 0) {
        return prev.map((r, i) => (i === exists ? { ...r, deviceMachId: mach } : r));
      }
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

  const visible = query
    ? rows.filter((r) => r.deviceMachId.toLowerCase().includes(query))
    : rows;

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>Device Details</h2>
          <div style={{ marginTop: 12 }}>
            <div className="form-grid">
              <label>
                Device ID
                <input value={form.deviceId} onChange={onChange("deviceId")} className="input" placeholder="Device ID" />
              </label>

              <label>
                Device Mach ID
                <input value={form.deviceMachId} onChange={onChange("deviceMachId")} className="input" placeholder="Machine ID" />
              </label>
            </div>

            <div className="controls">
              <button onClick={handleDelete} className="btn">Delete</button>
              <button onClick={handleClear} className="btn">Clear</button>
              <button onClick={handleSearch} className="btn">Search</button>
              <button onClick={handleSave} className="btn save">Save</button>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th className="sl">SL No.</th>
                  <th>Device ID</th>
                  <th>Device Mach ID</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={3} style={{ padding: 14, textAlign: "center" }}>No records</td>
                  </tr>
                ) : (
                  visible.map((r, i) => (
                    <tr key={r.deviceId} onClick={() => handleRowClick(r)}>
                      <td className="sl">{i + 1}</td>
                      <td>{r.deviceId}</td>
                      <td>{r.deviceMachId}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            <p className="hint">Tip: click a row to load it into the form for editing.</p>
          </div>
        </div>
      </div>
    </div>
  );
}