import React, { useState } from "react";

export default function MeterStatus() {
  const [meterStatus, setMeterStatus] = useState("");
  const [rows, setRows] = useState([
    { id: 1, status: "Active" },
    { id: 2, status: "Faulty" },
  ]);
  const [editingIndex, setEditingIndex] = useState(null);
  const [filter, setFilter] = useState("");

  function resetForm() {
    setMeterStatus("");
    setEditingIndex(null);
    setFilter("");
  }

  function handleSave() {
    const val = meterStatus.trim();
    if (!val) {
      alert("Enter meter status before saving.");
      return;
    }

    if (editingIndex !== null) {
      setRows((prev) => {
        const copy = [...prev];
        copy[editingIndex] = { ...copy[editingIndex], status: val };
        return copy;
      });
      resetForm();
      return;
    }

    const exists = rows.findIndex((r) => r.status.toLowerCase() === val.toLowerCase());
    if (exists >= 0) {
      if (!window.confirm("An identical status exists – update it?")) return;
      setRows((prev) => {
        const copy = [...prev];
        copy[exists] = { ...copy[exists], status: val };
        return copy;
      });
    } else {
      setRows((prev) => [...prev, { id: prev.length + 1, status: val }]);
    }
    resetForm();
  }

  function handleDelete() {
    if (editingIndex === null) {
      alert("Select a row to delete (click a row to select it).");
      return;
    }
    if (!window.confirm("Delete selected meter status?")) return;
    setRows((prev) => prev.filter((_, i) => i !== editingIndex));
    resetForm();
  }

  function handleSearch() {
    setFilter(meterStatus.trim().toLowerCase());
  }

  const visible = filter ? rows.filter((r) => r.status.toLowerCase().includes(filter)) : rows;

  function handleRowClick(index) {
    const r = rows[index];
    setMeterStatus(r.status);
    setEditingIndex(index);
  }

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>Meter Status</h2>
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
              <label style={{ minWidth: 110 }}>Meter Status</label>
              <input className="input" value={meterStatus} onChange={(e) => setMeterStatus(e.target.value)} placeholder="e.g. Active / Faulty / Removed" />
            </div>

            <div className="controls">
              <button className="btn" onClick={handleDelete}>Delete</button>
              <button className="btn" onClick={resetForm}>Clear</button>
              <button className="btn" onClick={handleSearch}>Search</button>
              <button className="btn save" onClick={handleSave}>Save</button>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th className="sl">SL No.</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr><td colSpan={3} style={{ textAlign: "center", padding: 14 }}>No records</td></tr>
                ) : (
                  visible.map((r, i) => (
                    <tr key={r.id} onClick={() => handleRowClick(i)}>
                      <td className="sl">{i + 1}</td>
                      <td>{r.status}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button className="btn" onClick={(e) => { e.stopPropagation(); setMeterStatus(r.status); setEditingIndex(i); }}>Edit</button>
                          <button className="btn" onClick={(e) => { e.stopPropagation(); setRows((p) => p.filter((x) => x.id !== r.id)); resetForm(); }}>Delete</button>
                        </div>
                      </td>
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