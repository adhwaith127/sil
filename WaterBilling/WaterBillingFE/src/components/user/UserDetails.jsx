import React, { useState } from "react";

export default function UserDetails() {
  const [form, setForm] = useState({ code: "", name: "", pwd: "" });
  const [rows, setRows] = useState([{ id: 1, code: "1", name: "BELLIYAPPA", pwdMasked: "******" }]);
  const [filter, setFilter] = useState("");
  const [editingIndex, setEditingIndex] = useState(null);

  const resetForm = () => { setForm({ code: "", name: "", pwd: "" }); setEditingIndex(null); };
  const findIndexByCode = (code) => rows.findIndex((r) => r.code === code);

  const handleSave = () => {
    const code = form.code.trim();
    const name = form.name.trim();
    const pwd = form.pwd;
    if (!code || !name) { window.alert("Please enter both Operator Code and Operator Name."); return; }
    const idx = findIndexByCode(code);
    if (idx >= 0 && editingIndex === null) {
      if (!window.confirm("Operator code exists – update existing record?")) return;
      const copy = [...rows];
      copy[idx] = { ...copy[idx], name, pwdMasked: pwd ? "******" : copy[idx].pwdMasked };
      setRows(copy);
    } else if (editingIndex !== null) {
      const copy = [...rows];
      copy[editingIndex] = { ...copy[editingIndex], code, name, pwdMasked: pwd ? "******" : copy[editingIndex].pwdMasked };
      setRows(copy);
    } else {
      setRows((prev) => [...prev, { id: prev.length + 1, code, name, pwdMasked: pwd ? "******" : "" }]);
    }
    resetForm();
    setFilter("");
  };

  const handleDelete = () => {
    const code = form.code.trim();
    if (!code) { window.alert("Enter Operator Code to delete."); return; }
    const idx = findIndexByCode(code);
    if (idx < 0) { window.alert("No such Operator Code."); return; }
    if (!window.confirm("Delete this operator?")) return;
    setRows(rows.filter((r) => r.code !== code));
    resetForm();
    setFilter("");
  };

  const handleClear = () => { resetForm(); setFilter(""); };
  const handleSearch = () => setFilter(form.name.trim());
  const handleRowClick = (index) => { const row = rows[index]; setForm({ code: row.code, name: row.name, pwd: "" }); setEditingIndex(index); };
  const visibleRows = filter ? rows.filter((r) => r.name.toLowerCase().includes(filter.toLowerCase())) : rows;

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>Operator Details</h2>
          <div style={{ marginTop: 12 }}>
            <div className="form-grid">
              <label>
                Operator Code
                <input className="input" value={form.code} onChange={(e) => setForm((s) => ({ ...s, code: e.target.value }))} />
              </label>
              <label>
                Operator Name
                <input className="input" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
              </label>
              <label>
                Operator Pwd
                <input className="input" type="password" value={form.pwd} onChange={(e) => setForm((s) => ({ ...s, pwd: e.target.value }))} />
              </label>
            </div>

            <div className="controls">
              <button className="btn" onClick={handleDelete}>Delete</button>
              <button className="btn" onClick={handleClear}>Clear</button>
              <button className="btn" onClick={handleSearch}>Search</button>
              <button className="btn save" onClick={handleSave}>Save</button>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th className="sl">SL No.</th>
                  <th>Code</th>
                  <th>Name</th>
                  <th>Password</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: 14 }}>No records</td></tr>
                ) : (
                  visibleRows.map((r, i) => (
                    <tr key={r.code} onClick={() => handleRowClick(rows.indexOf(r))}>
                      <td className="sl">{i + 1}</td>
                      <td>{r.code}</td>
                      <td>{r.name}</td>
                      <td>{r.pwdMasked}</td>
                    </tr>
                  ))
                )}
              </tbody>
              </table>

            <p className="hint">Tip: Fill the fields and click <strong>Save</strong> to add/update. Click a row to load it.</p>
          </div>
        </div>
      </div>
    </div>
  );
}