import React, { useState } from "react";

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
    alert("Show report clicked");
  };

  const handleExport = () => {
    alert("Export clicked");
  };

  return (
    <div style={{ padding: "20px" }}>
      <div style={{ maxWidth: "800px", margin: "0 auto", background: "white", borderRadius: "8px", padding: "24px" }}>
        <h2 style={{ textAlign: "center", margin: "0 0 20px 0" }}>Bill Report</h2>

        <div style={{ marginTop: 12 }}>
          <fieldset style={{ border: "1px solid #e6eef8", borderRadius: 8, padding: 12 }}>
            <legend style={{ color: "#2563eb", fontWeight: 600 }}>Sorting Order</legend>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <input type="radio" checked={sorting === "date"} onChange={() => setSorting("date")} />
                Date Sorting
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <input type="radio" checked={sorting === "name"} onChange={() => setSorting("name")} />
                Customer Name Sorting
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <input type="radio" checked={sorting === "code"} onChange={() => setSorting("code")} />
                Customer Code Sorting
              </label>
            </div>
          </fieldset>

          <div style={{ display: "flex", gap: 24, marginTop: 16 }}>
            <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input type="radio" checked={reportType === "yearly"} onChange={() => setReportType("yearly")} />
              Yearly Report
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input type="radio" checked={reportType === "general"} onChange={() => setReportType("general")} />
              General Report
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <input type="radio" checked={reportType === "export"} onChange={() => setReportType("export")} />
              Bill Export
            </label>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
            <label>
              <span style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>From</span>
              <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="input" />
            </label>
            <label>
              <span style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>To</span>
              <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="input" />
            </label>
          </div>

          <label style={{ display: "block", marginTop: 16 }}>
            <span style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>Customer Code / Name</span>
            <input type="text" value={customerCode} onChange={(e) => setCustomerCode(e.target.value)} className="input" placeholder="Enter customer code or name" />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16, marginTop: 16 }}>
            <label>
              <span style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>Operator</span>
              <select value={operator} onChange={(e) => setOperator(e.target.value)} className="input">
                <option>ALL</option>
                <option>Operator 1</option>
                <option>Operator 2</option>
              </select>
            </label>
            <label>
              <span style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>Palmtec</span>
              <select value={palmtec} onChange={(e) => setPalmtec(e.target.value)} className="input">
                <option>ALL</option>
                <option>Palmtec 1</option>
                <option>Palmtec 2</option>
              </select>
            </label>
            <label>
              <span style={{ display: "block", fontSize: "14px", marginBottom: "4px" }}>Zone</span>
              <select value={zone} onChange={(e) => setZone(e.target.value)} className="input">
                <option>ALL</option>
                <option>Zone 1</option>
                <option>Zone 2</option>
              </select>
            </label>
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: 24, marginTop: 24 }}>
            <button onClick={handleShow} className="btn">Show</button>
            <button onClick={handleExport} className="btn">Export</button>
          </div>
        </div>
      </div>
    </div>
  );
}