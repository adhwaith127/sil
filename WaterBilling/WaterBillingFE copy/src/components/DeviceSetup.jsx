import React, { useState } from "react";
import "../styles/DeviceSetup.css";

export default function DeviceSetup() {
  const [form, setForm] = useState({
    palmtecId: "",
    operator: "",
    mainDisplay1: "",
    mainDisplay2: "",
    header1: "",
    header2: "",
    header3: "",
    header4: "",
    footer1: "",
    footer2: "",
    paperFeed: "4",
    numberOfDial: "5",
    multiplicationFactor: "1",
    checkboxes: {}
  });

  const onChange = (k) => (e) => setForm(s => ({ ...s, [k]: e.target.value }));
  const onCheck = (k) => (e) => setForm(s => ({ ...s, checkboxes: { ...s.checkboxes, [k]: e.target.checked } }));

  function onClear(){
    setForm({
      palmtecId:"", operator:"", mainDisplay1:"", mainDisplay2:"", header1:"", header2:"", header3:"", header4:"", footer1:"", footer2:"",
      paperFeed:"4", numberOfDial:"5", multiplicationFactor:"1", checkboxes:{}
    });
  }

  function onSave(){
    alert("Settings saved (demo). Open console for payload.");
    console.log("Device Setup:", form);
  }

  const checkItems = ['Palmtec ID','Consumer Name','Consumer Code','Address','Ward','Phone No','Previous Reading','Previous date','Previous Balance','Total Due','Operator','Area','Bill SMS','Payment SMS','Due SMS','Enable Amount in Receipt','Fine Amount','Other Charges','Duplicate Bill'];

  return (
    <div className="device-setup">
      <div className="device-setup__card" role="region" aria-label="Device setup">
        <h2 className="device-setup__title">DEVICE SETUP</h2>

        <div className="device-setup__grid">
          <label className="device-setup__label">
            Device ID
            <select className="device-setup__select" value={form.palmtecId} onChange={onChange('palmtecId')}>
              <option value="">Select</option>
              <option>PAF106</option>
            </select>
          </label>

          <label className="device-setup__label">
            Operator
            <select className="device-setup__select" value={form.operator} onChange={onChange('operator')}>
              <option value="">Select</option>
              <option>Op1</option>
            </select>
          </label>

          <label className="device-setup__label">
            Main Display1
            <input className="device-setup__input" value={form.mainDisplay1} onChange={onChange('mainDisplay1')} />
          </label>

          <label className="device-setup__label">
            Main Display2
            <input className="device-setup__input" value={form.mainDisplay2} onChange={onChange('mainDisplay2')} />
          </label>

          <label className="device-setup__label">
            Header 1
            <input className="device-setup__input" value={form.header1} onChange={onChange('header1')} />
          </label>

          <label className="device-setup__label">
            Header 2
            <input className="device-setup__input" value={form.header2} onChange={onChange('header2')} />
          </label>

          <label className="device-setup__label">
            Header 3
            <input className="device-setup__input" value={form.header3} onChange={onChange('header3')} />
          </label>

          <label className="device-setup__label">
            Header 4
            <input className="device-setup__input" value={form.header4} onChange={onChange('header4')} />
          </label>

          <label className="device-setup__label">
            Footer 1
            <input className="device-setup__input" value={form.footer1} onChange={onChange('footer1')} />
          </label>

          <label className="device-setup__label">
            Footer 2
            <input className="device-setup__input" value={form.footer2} onChange={onChange('footer2')} />
          </label>

          <label className="device-setup__label">
            Paper Feed
            <input className="device-setup__input" value={form.paperFeed} onChange={onChange('paperFeed')} />
          </label>

          <label className="device-setup__label">
            Number of Dial
            <input className="device-setup__input" value={form.numberOfDial} onChange={onChange('numberOfDial')} />
          </label>

          <label className="device-setup__label">
            Multiplication Factor
            <input className="device-setup__input" value={form.multiplicationFactor} onChange={onChange('multiplicationFactor')} />
          </label>
        </div>

        <div className="device-setup__checkbox-group" role="group" aria-label="Receipt options">
          {checkItems.map(cb => (
            <label key={cb} className="device-setup__checkbox">
              <input type="checkbox" checked={!!form.checkboxes[cb]} onChange={onCheck(cb)} /> {cb}
            </label>
          ))}
        </div>

        <div className="device-setup__actions">
          <button onClick={onClear} className="device-setup__btn">Clear</button>
          <button onClick={onSave} className="device-setup__btn device-setup__btn--primary">Save/Download</button>
        </div>
      </div>
    </div>
  );
}
