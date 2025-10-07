import React, { useMemo, useState } from "react";
import "../styles/ConsumerType.css";

/**
 * ConsumerType.jsx
 * - Compact form (code & name) with proper spacing
 * - Moderate search box (doesn't take full width)
 * - Live filtering: empty search shows all rows
 * - Reset clears search and restores full list
 */

const initialData = [
  { id: 2, code: "2", name: "COMMERCIAL" },
  { id: 1, code: "1", name: "DOMESTIC" },
  { id: 3, code: "3", name: "SEMIDOMESTIC" },
];

export default function ConsumerTypeManager() {
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  // master list
  const [items, setItems] = useState(initialData);

  // visibleRows derived from items + searchQuery (live)
  const visible = useMemo(() => {
    const q = (searchQuery || "").trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (r) => r.name.toLowerCase().includes(q) || String(r.code).includes(q)
    );
  }, [items, searchQuery]);

  function onSave() {
    const c = (code || "").trim();
    const n = (name || "").trim();
    if (!c || !n) return alert("Enter Code and Name");
    const exists = items.findIndex((r) => r.code === c);
    if (exists >= 0) {
      setItems((prev) => prev.map((r, i) => (i === exists ? { ...r, name: n } : r)));
    } else {
      setItems((prev) => [...prev, { id: prev.length + 1, code: c, name: n }]);
    }
    setCode("");
    setName("");
    setSearchQuery("");
  }

  function onDelete() {
    const c = (code || "").trim();
    if (!c) return alert("Enter Code to delete");
    setItems((prev) => prev.filter((r) => r.code !== c));
    setCode("");
    setName("");
    setSearchQuery("");
  }

  function onClear() {
    setCode("");
    setName("");
    setSearchQuery("");
  }

  function onResetSearch() {
    setSearchQuery("");
  }

  return (
    <div className="consumer-type">
      <div className="consumer-type__card">
        <h2 className="consumer-type__title">CONSUMER TYPE</h2>

        {/* compact single-line form */}
        <div className="consumer-type__row">
          <label className="consumer-type__row-item">
            <span className="consumer-type__row-label">Consumer Type Code</span>
            <input
              className="consumer-type__row-input consumer-type__row-input--code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Code"
              inputMode="numeric"
            />
          </label>

          <div className="consumer-type__spacer-small" />

          <label className="consumer-type__row-item">
            <span className="consumer-type__row-label">Consumer Type Name</span>
            <input
              className="consumer-type__row-input consumer-type__row-input--name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Name"
            />
          </label>
        </div>

        {/* actions row (separate, not in search) */}
        <div className="consumer-type__actions">
          <button onClick={onDelete} className="consumer-type__button">Delete</button>
          <button onClick={onClear} className="consumer-type__button">Clear</button>
          <button onClick={onSave} className="consumer-type__button consumer-type__button--save">Save</button>
        </div>

        {/* search row - moderate width, live filtering */}
        <div className="consumer-type__search">
          <label className="consumer-type__search-label" htmlFor="ct-search">Search:</label>
          <input
            id="ct-search"
            className="consumer-type__search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name or code"
            aria-label="Search consumer type"
          />
          <button onClick={onResetSearch} className="consumer-type__button">Reset</button>
        </div>

        {/* table */}
        <div className="consumer-type__table-wrap">
          <table className="consumer-type__table" role="table" aria-label="Consumer types">
            <thead>
              <tr>
                <th>SL No.</th>
                <th>Code</th>
                <th>Consumer Type Name</th>
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 ? (
                <tr><td colSpan="3" style={{ textAlign: "center", padding: 12 }}>No records</td></tr>
              ) : (
                visible.map((r, i) => (
                  <tr key={r.code} onClick={() => { setCode(r.code); setName(r.name); }}>
                    <td>{i + 1}</td>
                    <td>{r.code}</td>
                    <td>{r.name}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}