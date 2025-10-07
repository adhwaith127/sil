import React, { useState } from "react";

export default function WardManager() {
  const [wardId, setWardId] = useState("");
  const [wardName, setWardName] = useState("");
  const [rows, setRows] = useState([
    { id: "1", name: "example" },
    { id: "2", name: "sample" },
  ]);
  const [filter, setFilter] = useState("");

  const onSave = () => {
    if (!wardId.trim() || !wardName.trim()) return;
    setRows((prev) => [...prev, { id: wardId.trim(), name: wardName.trim() }]);
    setWardId("");
    setWardName("");
  };

  const onDelete = () => {
    if (!wardId.trim()) return;
    setRows((prev) => prev.filter((r) => r.id !== wardId.trim()));
    setWardId("");
    setWardName("");
  };

  const onClear = () => {
    setWardId("");
    setWardName("");
    setFilter("");
  };

  const onSearch = () => setFilter(wardName.trim());
  const visible = rows.filter((r) => (filter ? r.name.toLowerCase().includes(filter.toLowerCase()) : true));

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>Ward Manager</h2>
          <div style={{ marginTop: 12 }}>
            <div className="form-grid">
              <label>
                Ward ID
                <input className="input" value={wardId} onChange={(e) => setWardId(e.target.value)} placeholder="Enter ID" />
              </label>
              <label>
                Ward Name
                <input className="input" value={wardName} onChange={(e) => setWardName(e.target.value)} placeholder="Enter ward" />
              </label>
            </div>

            <div className="controls">
              <button className="btn" onClick={onDelete}>Delete</button>
              <button className="btn" onClick={onClear}>Clear</button>
              <button className="btn" onClick={onSearch}>Search</button>
              <button className="btn save" onClick={onSave}>Save</button>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th className="sl">SLNO</th>
                  <th>Ward ID</th>
                  <th>Ward Name</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr>
                    <td colSpan={4} style={{ textAlign: "center", padding: 18 }}>No results</td>
                  </tr>
                ) : (
                  visible.map((r, i) => (
                    <tr key={r.id}>
                      <td className="sl">{i + 1}</td>
                      <td>{r.id}</td>
                      <td>{r.name}</td>
                      <td>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button className="btn" onClick={() => { setWardId(r.id); setWardName(r.name); }}>Edit</button>
                          <button className="btn" onClick={(e) => { e.stopPropagation(); setRows((prev) => prev.filter((x) => x.id !== r.id)); }}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            <p className="hint">Tip: click a row's Edit to load it into the form.</p>
          </div>
        </div>
      </div>
    </div>
  );
}