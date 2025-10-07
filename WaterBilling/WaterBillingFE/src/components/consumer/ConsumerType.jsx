import React, { useState } from "react";

export default function ConsumerType() {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [filter, setFilter] = useState("");
  const [rows, setRows] = useState([
    { id: 2, code: "2", name: "COMMERCIAL" },
    { id: 1, code: "1", name: "DOMESTIC" },
    { id: 3, code: "3", name: "SEMIDOMESTIC" },
  ]);

  function onSave() {
    const c = code.trim();
    const n = name.trim();
    if (!c || !n) return alert("Enter Code and Name");

    const idx = rows.findIndex(r => r.code === c);
    if (idx >= 0) {
      setRows(prev => prev.map((r, i) => i === idx ? { ...r, name: n } : r));
    } else {
      setRows(prev => [...prev, { id: prev.length + 1, code: c, name: n }]);
    }
    setCode("");
    setName("");
    setFilter("");
  }

  function onDelete() {
    const c = code.trim();
    if (!c) return alert("Enter Code to delete");
    setRows(prev => prev.filter(r => r.code !== c));
    setCode("");
    setName("");
  }

  function onClear() {
    setCode("");
    setName("");
    setFilter("");
  }

  function onSearch() {
    setFilter(name.trim());
  }

  const visible = filter ? rows.filter(r => r.name.toLowerCase().includes(filter.toLowerCase())) : rows;

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>Consumer Type</h2>
          <div style={{ marginTop: 12 }}>
            <div className="form-grid">
              <label>
                Consumer Type Code
                <input value={code} onChange={e => setCode(e.target.value)} className="input" placeholder="Code" />
              </label>

              <label>
                Consumer Type Name
                <input value={name} onChange={e => setName(e.target.value)} className="input" placeholder="Enter consumer type name" />
              </label>
            </div>

            <div className="controls">
              <button onClick={onDelete} className="btn">Delete</button>
              <button onClick={onClear} className="btn">Clear</button>
              <button onClick={onSave} className="btn save">Save</button>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th className="sl">SL No.</th>
                  <th>Code</th>
                  <th>Consumer Type Name</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr><td colSpan={3} style={{ padding: 14, textAlign: "center" }}>No records</td></tr>
                ) : (
                  visible.map((r, i) => (
                    <tr key={r.code} onClick={() => { setCode(r.code); setName(r.name); }}>
                      <td className="sl">{i + 1}</td>
                      <td>{r.code}</td>
                      <td>{r.name}</td>
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