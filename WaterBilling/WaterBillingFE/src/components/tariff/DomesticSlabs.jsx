import React, { useState } from "react";

export default function DomesticSlabs() {
  const [form, setForm] = useState({
    consumerType: "",
    fixedCharge: "",
    fromUnit: "",
    toUnit: "",
    amount: "",
    perUnit: "",
  });

  const [rows, setRows] = useState([
    { id: 1, consumerType: "Residential", fixedCharge: "50", fromUnit: "0", toUnit: "50", amount: "100", perUnit: "2" },
  ]);

  const [editingIndex, setEditingIndex] = useState(null);
  const [filter, setFilter] = useState("");

  function resetForm() {
    setForm({ consumerType: "", fixedCharge: "", fromUnit: "", toUnit: "", amount: "", perUnit: "" });
    setEditingIndex(null);
    setFilter("");
  }

  function validateForm() {
    if (!form.consumerType.trim()) { alert("Please select Consumer Type."); return false; }
    if (form.fromUnit === "" || form.toUnit === "" || form.amount === "") { alert("Please enter From Unit, To Unit and Amount."); return false; }
    const from = Number(form.fromUnit), to = Number(form.toUnit);
    if (Number.isNaN(from) || Number.isNaN(to) || from < 0 || to < 0 || to < from) { alert("Please enter valid unit range (To Unit should be >= From Unit)."); return false; }
    return true;
  }

  function handleSave() {
    if (!validateForm()) return;
    const entry = {
      id: editingIndex !== null ? rows[editingIndex].id : rows.length + 1,
      consumerType: form.consumerType,
      fixedCharge: form.fixedCharge.trim(),
      fromUnit: form.fromUnit.trim(),
      toUnit: form.toUnit.trim(),
      amount: form.amount.trim(),
      perUnit: form.perUnit.trim()
    };
    if (editingIndex !== null) {
      const copy = [...rows];
      copy[editingIndex] = entry;
      setRows(copy);
    } else {
      setRows((r) => [...r, entry]);
    }
    resetForm();
  }

  function handleDelete() {
    if (editingIndex === null) { alert("Click a row to select the slab to delete."); return; }
    if (!window.confirm("Delete selected slab?")) return;
    setRows((r) => r.filter((_, idx) => idx !== editingIndex));
    resetForm();
  }

  function handleRowClick(idx) {
    const r = rows[idx];
    setForm({ consumerType: r.consumerType, fixedCharge: r.fixedCharge, fromUnit: r.fromUnit, toUnit: r.toUnit, amount: r.amount, perUnit: r.perUnit });
    setEditingIndex(idx);
  }

  const visible = filter ? rows.filter((r) => r.consumerType.toLowerCase().includes(filter.toLowerCase())) : rows;

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>Domestic Slabs</h2>
          <div style={{ marginTop: 12 }}>
            <div className="form-grid">
              <label>
                Consumer Type
                <select className="input" value={form.consumerType} onChange={(e) => setForm((s) => ({ ...s, consumerType: e.target.value }))}>
                  <option value="">-- select --</option>
                  <option>Residential</option>
                  <option>Commercial</option>
                  <option>Industrial</option>
                  <option>Agricultural</option>
                </select>
              </label>

              <label>
                Fixed Charge
                <input className="input" type="number" min="0" value={form.fixedCharge} onChange={(e) => setForm((s) => ({ ...s, fixedCharge: e.target.value }))} />
              </label>

              <label>
                From Unit
                <input className="input" type="number" min="0" value={form.fromUnit} onChange={(e) => setForm((s) => ({ ...s, fromUnit: e.target.value }))} />
              </label>

              <label>
                To Unit
                <input className="input" type="number" min="0" value={form.toUnit} onChange={(e) => setForm((s) => ({ ...s, toUnit: e.target.value }))} />
              </label>

              <label>
                Amount
                <input className="input" type="number" min="0" value={form.amount} onChange={(e) => setForm((s) => ({ ...s, amount: e.target.value }))} />
              </label>

              <label>
                Per Unit
                <input className="input" type="number" min="0" value={form.perUnit} onChange={(e) => setForm((s) => ({ ...s, perUnit: e.target.value }))} />
              </label>
            </div>

            <div className="controls">
              <button className="btn" onClick={handleDelete}>Delete</button>
              <button className="btn" onClick={resetForm}>Clear</button>
              <button className="btn" onClick={() => setFilter(form.consumerType.trim().toLowerCase())}>Search</button>
              <button className="btn save" onClick={handleSave}>Save</button>
            </div>

            <table className="table">
              <thead>
                <tr>
                  <th className="sl">SL No.</th>
                  <th>Consumer Type</th>
                  <th>From Unit</th>
                  <th>To Unit</th>
                  <th>Amount</th>
                  <th>Per Unit</th>
                </tr>
              </thead>
              <tbody>
                {visible.length === 0 ? (
                  <tr><td colSpan={6} style={{ textAlign: 'center', padding: 18 }}>No slabs defined</td></tr>
                ) : (
                  visible.map((r, idx) => (
                    <tr key={r.id} onClick={() => handleRowClick(rows.indexOf(r))}>
                      <td className="sl">{idx + 1}</td>
                      <td>{r.consumerType}</td>
                      <td>{r.fromUnit}</td>
                      <td>{r.toUnit}</td>
                      <td>{r.amount}</td>
                      <td>{r.perUnit}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            <p className="hint">Tip: Click a row to load it into the form for editing. Use <strong>Save</strong> to add/update slabs.</p>
          </div>
        </div>
      </div>
    </div>
  );
}