import React, { useState } from "react";
import "../styles/BillReport.css";

export default function BillReport() {
  const [sorting, setSorting] = useState("date");
  const [reportType, setReportType] = useState("general");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [customerCode, setCustomerCode] = useState("");
  const [operator, setOperator] = useState("ALL");
  const [palmtec, setPalmtec] = useState("ALL");
  const [zone, setZone] = useState("ALL");

  const handleShow = () => {
    alert(`Show: ${sorting}, ${reportType}, ${fromDate} -> ${toDate}, ${customerCode}`);
  };

  const handleExport = () => {
    alert("Export clicked (demo)");
  };

  return (
    <div className="bill-report">
      <div className="bill-report__card" role="region" aria-label="Bill Report">
        <h2 className="bill-report__title">Bill Report</h2>

        <fieldset className="bill-report__fieldset" aria-label="Sorting order">
          <legend className="bill-report__legend">Sorting Order</legend>
          <div className="bill-report__controls">
            <label>
              <input type="radio" checked={sorting === "date"} onChange={() => setSorting("date")} /> Date
            </label>
            <label>
              <input type="radio" checked={sorting === "name"} onChange={() => setSorting("name")} /> Name
            </label>
            <label>
              <input type="radio" checked={sorting === "code"} onChange={() => setSorting("code")} /> Code
            </label>
          </div>
        </fieldset>

        <div className="bill-report__controls" role="radiogroup" aria-label="Report type">
          <label><input type="radio" checked={reportType === "yearly"} onChange={() => setReportType("yearly")} /> Yearly</label>
          <label><input type="radio" checked={reportType === "general"} onChange={() => setReportType("general")} /> General</label>
          <label><input type="radio" checked={reportType === "export"} onChange={() => setReportType("export")} /> Export</label>
        </div>

        <div className="bill-report__grid">
          <label className="bill-report__label">
            From
            <input className="bill-report__input" type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} />
          </label>

          <label className="bill-report__label">
            To
            <input className="bill-report__input" type="date" value={toDate} onChange={e => setToDate(e.target.value)} />
          </label>
        </div>

        <label className="bill-report__label" style={{ marginBottom: 8 }}>
          Customer Code / Name
          <input className="bill-report__input" value={customerCode} onChange={e => setCustomerCode(e.target.value)} placeholder="Code or name" />
        </label>

        <div className="bill-report__grid">
          <label className="bill-report__label">
            Operator
            <select className="bill-report__select" value={operator} onChange={e => setOperator(e.target.value)}>
              <option>ALL</option>
              <option>Operator 1</option>
            </select>
          </label>

          <label className="bill-report__label">
            Palmtec
            <select className="bill-report__select" value={palmtec} onChange={e => setPalmtec(e.target.value)}>
              <option>ALL</option>
            </select>
          </label>

          <label className="bill-report__label">
            Zone
            <select className="bill-report__select" value={zone} onChange={e => setZone(e.target.value)}>
              <option>ALL</option>
            </select>
          </label>
        </div>

        <div className="bill-report__buttons">
          <button className="bill-report__button" onClick={handleShow}>Show</button>
          <button className="bill-report__button bill-report__button--primary" onClick={handleExport}>Export</button>
        </div>
      </div>
    </div>
  );
}
