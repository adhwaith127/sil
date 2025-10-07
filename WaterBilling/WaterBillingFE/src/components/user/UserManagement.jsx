import React, { useState } from "react";

export default function UserManagement() {
  const [form, setForm] = useState({
    userName: "",
    privilege: "",
    password: "",
    cardiumPassword: "",
    wardId: "",
  });

  const [rows, setRows] = useState([
    { id: 1, userName: "admin", privilege: "Administrator", wardId: "W1" },
    { id: 2, userName: "john", privilege: "Operator", wardId: "W2" },
  ]);

  const [editingIndex, setEditingIndex] = useState(null);
  const [filter, setFilter] = useState("");

  const sampleUserNames = ["admin", "john", "sarah", "guest"];
  const samplePrivileges = ["Administrator", "Operator", "Viewer"];

  function resetForm() {
    setForm({ userName: "", privilege: "", password: "", cardiumPassword: "", wardId: "" });
    setEditingIndex(null);
    setFilter("");
  }

  function handleSave() {
    const { userName, privilege } = form;
    if (!userName.trim() || !privilege.trim()) {
      alert("Please enter User Name and Privilege.");
      return;
    }

    if (editingIndex !== null) {
      setRows((prev) => {
        const copy = [...prev];
        copy[editingIndex] = { ...copy[editingIndex], userName: form.userName.trim(), privilege: form.privilege.trim(), wardId: form.wardId.trim() };
        return copy;
      });
      resetForm();
      return;
    }

    const existing = rows.findIndex(r => r.userName.toLowerCase() === userName.trim().toLowerCase());
    if (existing >= 0) {
      if (!window.confirm("User already exists. Update existing user?")) return;
      setRows((prev) => {
        const copy = [...prev];
        copy[existing] = { ...copy[existing], userName: form.userName.trim(), privilege: form.privilege.trim(), wardId: form.wardId.trim() };
        return copy;
      });
      resetForm();
      return;
    }

    setRows((prev) => [...prev, { id: prev.length + 1, userName: form.userName.trim(), privilege: form.privilege.trim(), wardId: form.wardId.trim() }]);
    resetForm();
  }

  function handleDelete() {
    if (!form.userName.trim()) { alert("Enter User Name to delete."); return; }
    const idx = rows.findIndex(r => r.userName.toLowerCase() === form.userName.trim().toLowerCase());
    if (idx < 0) { alert("No such user."); return; }
    if (!window.confirm("Delete this user?")) return;
    setRows(prev => prev.filter((_, i) => i !== idx));
    resetForm();
  }

  function handleSearch() {
    setFilter(form.userName.trim().toLowerCase());
  }

  const visible = filter ? rows.filter(r => r.userName.toLowerCase().includes(filter)) : rows;

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>User Management (Web)</h2>
          <div style={{ marginTop: 12 }}>
            <div className="form-grid">
              <label>
                User Name
                <select className="input" value={form.userName} onChange={e => setForm(s => ({ ...s, userName: e.target.value }))}>
                  <option value="">-- select --</option>
                  {sampleUserNames.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </label>

              <label>
                User Privilege
                <select className="input" value={form.privilege} onChange={e => setForm(s => ({ ...s, privilege: e.target.value }))}>
                  <option value="">-- select --</option>
                  {samplePrivileges.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
              </label>

              <label>
                Password
                <input className="input" type="password" value={form.password} onChange={e => setForm(s => ({ ...s, password: e.target.value }))} />
              </label>

              <label>
                Confirm Password
                <input className="input" type="password" value={form.cardiumPassword} onChange={e => setForm(s => ({ ...s, cardiumPassword: e.target.value }))} />
              </label>

              <label>
                Ward ID
                <input className="input" value={form.wardId} onChange={e => setForm(s => ({ ...s, wardId: e.target.value }))} placeholder="e.g. W1" />
              </label>
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
                  <th>User Name</th>
                  <th>User Privilege</th>
                  <th>Ward ID</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr><td colSpan={4} style={{ textAlign: 'center', padding: 14 }}>No records</td></tr>
                ) : (
                  visible.map((r, idx) => (
                    <tr key={r.id} onClick={() => { setForm({ userName: r.userName, privilege: r.privilege, password: "", cardiumPassword: "", wardId: r.wardId }); setEditingIndex(rows.indexOf(r)); }}>
                      <td className="sl">{idx + 1}</td>
                      <td>{r.userName}</td>
                      <td>{r.privilege}</td>
                      <td>{r.wardId}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            <p className="hint">Tip: Click a row to load it into the form for editing. Use <strong>Save</strong> to add/update.</p>
          </div>
        </div>
      </div>
    </div>
  );
}