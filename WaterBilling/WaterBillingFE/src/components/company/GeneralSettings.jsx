import React, { useState } from "react";

export default function GeneralSettings() {
  const [form, setForm] = useState({
    receiptLabel: "",
    header1: "",
    header2: "",
    header3: "",
    header4: "",
    footer1: "",
    footer2: "",
    logoPath: "",
    reprintConfirm: false,
    roundOff: false,
    roundType: "",
    roundMode: "",
    welcomeMsg: "",
  });

  const onChange = (k) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((s) => ({ ...s, [k]: value }));
  };

  const onBrowseLogo = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (f) setForm((s) => ({ ...s, logoPath: f.name }));
    };
    input.click();
  };

  const onSave = () => { console.log("Saving billing config:", form); alert("Configuration saved (demo). Check console for payload."); };
  const onPrinterSetup = () => alert("Open printer setup (demo)");

  return (
    <div className="container">
      <div className="center-card">
        <div className="card">
          <h2>General Settings</h2>
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
              <label>
                Receipt Label
                <input className="input" value={form.receiptLabel} onChange={onChange("receiptLabel")} />
              </label>
              <label>
                Header 1
                <input className="input" value={form.header1} onChange={onChange("header1")} />
              </label>
              <label>
                Header 2
                <input className="input" value={form.header2} onChange={onChange("header2")} />
              </label>
              <label>
                Header 3
                <input className="input" value={form.header3} onChange={onChange("header3")} />
              </label>
              <label>
                Header 4
                <input className="input" value={form.header4} onChange={onChange("header4")} />
              </label>
              <label>
                Footer 1
                <input className="input" value={form.footer1} onChange={onChange("footer1")} />
              </label>
              <label>
                Footer 2
                <input className="input" value={form.footer2} onChange={onChange("footer2")} />
              </label>
              <label style={{ gridColumn: "span 2" }}>
                Logo Path
                <div style={{ display: "flex", gap: 8 }}>
                  <input className="input" value={form.logoPath} onChange={onChange("logoPath")} placeholder="Select logo file" />
                  <button className="btn" onClick={onBrowseLogo}>...</button>
                </div>
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={form.reprintConfirm} onChange={onChange("reprintConfirm")} /> Reprint Confirmation
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="checkbox" checked={form.roundOff} onChange={onChange("roundOff")} /> Round OFF
              </label>
              <label>
                Type
                <select className="input" value={form.roundType} onChange={onChange("roundType")}>
                  <option value="">--</option>
                  <option value="nearest">Nearest</option>
                  <option value="up">Up</option>
                  <option value="down">Down</option>
                </select>
              </label>
              <label>
                Mode
                <select className="input" value={form.roundMode} onChange={onChange("roundMode")}>
                  <option value="">--</option>
                  <option value="0.5">0.5</option>
                  <option value="1">1</option>
                  <option value="5">5</option>
                </select>
              </label>
            </div>

            <div className="controls" style={{ marginTop: 16 }}>
              <div style={{ flex: 1 }}>
                <label>Welcome Message
                  <input className="input" value={form.welcomeMsg} onChange={onChange("welcomeMsg")} />
                </label>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button className="btn" onClick={onPrinterSetup}>Printer Setup</button>
                <button className="btn save" onClick={onSave}>Save</button>
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}