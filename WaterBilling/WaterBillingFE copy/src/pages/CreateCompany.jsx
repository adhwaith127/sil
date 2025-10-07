import React from "react";
import "../styles/ConsumerDetails.css";

export default function CreateCompany() {
  return (
    <div className="consumer-details">
      <div className="consumer-details__card">
        <h2 className="consumer-details__title">Register Your Company</h2>
        <div style={{ display: "grid", gap: 10 }}>
          <label className="consumer-details__label">
            Company Name
            <input className="consumer-details__input" placeholder="Enter company name" />
          </label>

          <label className="consumer-details__label">
            Address
            <input className="consumer-details__input" placeholder="Enter address" />
          </label>

          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button className="consumer-details__btn">Cancel</button>
            <button className="consumer-details__btn consumer-details__btn--primary">Save</button>
          </div>
        </div>
      </div>
    </div>
  );
}
