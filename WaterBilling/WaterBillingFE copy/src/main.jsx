import React from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import './index.css';
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";

import Layout from "./components/Layout";
import DashboardFull from "./components/DashboardFull";
import BillReport from "./components/BillReport";
import ConsumerDetails from "./components/ConsumerDetails";
import ConsumerType from "./components/ConsumerType";
import DeviceDetails from "./components/DeviceDetails";
import DeviceSetup from "./components/DeviceSetup";
import CreateCompany from "./pages/CreateCompany";

/* root route uses Layout which contains the navbar and <Outlet /> */
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <DashboardFull /> },            // path: '/'
      { path: "dashboard", element: <DashboardFull /> },     // path: '/dashboard'
      { path: "consumers", element: <ConsumerDetails /> },   // '/consumers'
      { path: "consumer-types", element: <ConsumerType /> }, // '/consumer-types'
      { path: "devices", element: <DeviceDetails /> },       // '/devices'
      { path: "device-setup", element: <DeviceSetup /> },   // '/device-setup'
      { path: "reports", element: <BillReport /> },          // '/reports'
      { path: "register", element: <CreateCompany /> },      // '/register'
      { path: "*", element: <Navigate to="/" replace /> },   // fallback
    ]
  }
]);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
);
