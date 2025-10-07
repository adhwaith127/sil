import React, { useRef, useState } from "react";
import "../styles/ConsumerDetails.css";

export default function ConsumerDetailsManager() {
  const [form, setForm] = useState({
    code: "",
    name: "",
    address1: "",
    address2: "",
    phone: "",
    email: "",
    ward: "",
    area: "",
    pendingAmount: "",
    meterNumber: "",
    previousReadingDate: "",
    previousReading: "",
    customerType: "",
    dmaDetail: "",
    zone: "",
    pipeDia: "",
    hscSize: "",
    consumerGps: "",
    memberFile: "",
  });

  const [rows, setRows] = useState([
    { id: 46, code: "46", name: "ABBU", address1: "", address2: "", phone: "9164404" },
    { id: 57, code: "57", name: "ABDUL AJIJ", address1: "", address2: "", phone: "8296780" },
    { id: 167, code: "167", name: "ABDUL BASHEER", address1: "", address2: "", phone: "9945933" },
  ]);

  const fileInputRef = useRef(null);

  const onChange = (k) => (e) => setForm(s => ({ ...s, [k]: e.target.value }));

  function onSave() {
    if (!form.code || !form.name) return alert("Please enter consumer code and name");
    const exists = rows.findIndex(r => r.code === form.code);
    if (exists >= 0) {
      setRows(prev => prev.map((r,i)=> i===exists ? { ...r, name: form.name, address1: form.address1, phone: form.phone } : r));
    } else {
      setRows(prev => [...prev, { id: prev.length+1, code: form.code, name: form.name, address1: form.address1, address2: form.address2, phone: form.phone }]);
    }
    alert("Saved (demo)");
  }

  function onDelete() {
    if (!form.code) return alert("Enter code to delete");
    setRows(prev => prev.filter(r => r.code !== form.code));
    onClear();
  }

  function onClear() {
    setForm({
      code: "", name: "", address1: "", address2: "", phone: "", email: "", ward: "", area: "", pendingAmount: "",
      meterNumber: "", previousReadingDate: "", previousReading: "", customerType: "", dmaDetail: "", zone: "",
      pipeDia: "", hscSize: "", consumerGps: "", memberFile: ""
    });
  }

  function onSearch() {
    const name = form.name.trim();
    if (!name) return alert("Enter name to search (demo)");
    const found = rows.filter(r => r.name.toLowerCase().includes(name.toLowerCase()));
    if (found.length === 0) alert("No matching records (demo)");
    else setRows(found);
  }

  function handleImportClick() {
    fileInputRef.current?.click();
  }

  function handleFileChange(e) {
    const f = e.target.files && e.target.files[0];
    if (f) setForm(s => ({ ...s, memberFile: f.name }));
  }

  return (
    <div className="consumer-details">
      <div className="consumer-details__card" role="region" aria-label="Consumer Details">
        <h2 className="consumer-details__title">CONSUMER DETAILS</h2>

        <div className="consumer-details__form" role="form" aria-label="consumer form">
          <label className="consumer-details__label">
            Consumer Code
            <input className="consumer-details__input" value={form.code} onChange={onChange('code')} />
          </label>

          <label className="consumer-details__label">
            Consumer Name
            <input className="consumer-details__input" value={form.name} onChange={onChange('name')} />
          </label>

          <label className="consumer-details__label">
            Address 1
            <input className="consumer-details__input" value={form.address1} onChange={onChange('address1')} />
          </label>

          <label className="consumer-details__label">
            Address 2
            <input className="consumer-details__input" value={form.address2} onChange={onChange('address2')} />
          </label>

          <label className="consumer-details__label">
            Phone Number
            <input className="consumer-details__input" value={form.phone} onChange={onChange('phone')} />
          </label>

          <label className="consumer-details__label">
            Email
            <input className="consumer-details__input" value={form.email} onChange={onChange('email')} />
          </label>

          <label className="consumer-details__label">
            Ward
            <select className="consumer-details__select" value={form.ward} onChange={onChange('ward')}>
              <option value="">Select</option>
              <option>W1</option>
            </select>
          </label>

          <label className="consumer-details__label">
            Area
            <input className="consumer-details__input" value={form.area} onChange={onChange('area')} />
          </label>

          <label className="consumer-details__label">
            Pending Amount
            <input className="consumer-details__input" value={form.pendingAmount} onChange={onChange('pendingAmount')} />
          </label>

          <label className="consumer-details__label">
            Meter Number
            <input className="consumer-details__input" value={form.meterNumber} onChange={onChange('meterNumber')} />
          </label>

          <label className="consumer-details__label">
            Previous reading Date
            <input className="consumer-details__input" type="date" value={form.previousReadingDate} onChange={onChange('previousReadingDate')} />
          </label>

          <label className="consumer-details__label">
            Previous reading
            <input className="consumer-details__input" value={form.previousReading} onChange={onChange('previousReading')} />
          </label>

          <label className="consumer-details__label">
            Customer Type
            <select className="consumer-details__select" value={form.customerType} onChange={onChange('customerType')}>
              <option value="">Select</option>
              <option>Residential</option>
            </select>
          </label>

          <label className="consumer-details__label">
            DMA Detail
            <input className="consumer-details__input" value={form.dmaDetail} onChange={onChange('dmaDetail')} />
          </label>

          <label className="consumer-details__label">
            Zone
            <input className="consumer-details__input" value={form.zone} onChange={onChange('zone')} />
          </label>

          <label className="consumer-details__label" style={{ gridColumn: "span 2" }}>
            Browse member file
            <div style={{ display: "flex", gap: 8 }}>
              <input className="consumer-details__input" value={form.memberFile} onChange={onChange('memberFile')} placeholder="Choose file..." />
              <button type="button" onClick={handleImportClick} className="consumer-details__btn">Import Excel</button>
              <input ref={fileInputRef} type="file" accept=".xlsx,.xls,.csv" onChange={handleFileChange} style={{ display: "none" }} />
            </div>
          </label>
        </div>

        <div className="consumer-details__actions">
          <div>
            <button className="consumer-details__btn">Export Excel</button>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={onDelete} className="consumer-details__btn">Delete</button>
            <button onClick={onClear} className="consumer-details__btn">Clear</button>
            <button onClick={onSearch} className="consumer-details__btn">Search</button>
            <button onClick={onSave} className="consumer-details__btn consumer-details__btn--primary">Save</button>
          </div>
        </div>

        <div className="consumer-details__table-wrap" role="region" aria-label="Consumer list">
          <table className="consumer-details__table">
            <thead>
              <tr>
                <th>SL No.</th>
                <th>Code</th>
                <th>Name</th>
                <th>Address1</th>
                <th>Address2</th>
                <th>Phone</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.code} onClick={() => setForm(s => ({ ...s, code: r.code, name: r.name, address1: r.address1, address2: r.address2, phone: r.phone }))}>
                  <td>{i + 1}</td>
                  <td>{r.code}</td>
                  <td>{r.name}</td>
                  <td>{r.address1}</td>
                  <td>{r.address2}</td>
                  <td>{r.phone}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
