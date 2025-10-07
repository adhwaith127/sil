import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import DashboardHome from './components/dashboard/DashboardHome';
import WardManager from './components/company/WardManager';
import GeneralSettings from './components/company/GeneralSettings';
import UserDetails from './components/user/UserDetails';
import UserManagement from './components/user/UserManagement';
import DomesticSlabs from './components/tariff/DomesticSlabs';
import MeterStatus from './components/tariff/MeterStatus';
import ConsumerType from './components/consumer/ConsumerType';
import ConsumerDetails from './components/consumer/ConsumerDetails';
import DeviceSetup from './components/device/DeviceSetup';
import DeviceDetails from './components/device/DeviceDetails';
import BillReport from './components/report/BillReport';
import ConsumerReport from './components/report/ConsumerReport';
import PaymentReport from './components/report/PaymentReport';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <DashboardHome />
      },
      {
        path: 'ward-details',
        element: <WardManager />
      },
      {
        path: 'general-settings',
        element: <GeneralSettings />
      },
      {
        path: 'mobile-user',
        element: <UserDetails />
      },
      {
        path: 'web-user',
        element: <UserManagement />
      },
      {
        path: 'domestic-tariff',
        element: <DomesticSlabs />
      },
      {
        path: 'meter-status',
        element: <MeterStatus />
      },
      {
        path: 'consumer-type',
        element: <ConsumerType />
      },
      {
        path: 'consumer-details',
        element: <ConsumerDetails />
      },
      {
        path: 'device-settings',
        element: <DeviceSetup />
      },
      {
        path: 'device-details',
        element: <DeviceDetails />
      },
      {
        path: 'bill-report',
        element: <BillReport />
      },
      {
        path: 'consumer-report',
        element: <ConsumerReport />
      },
      {
        path: 'payment-report',
        element: <PaymentReport />
      }
    ]
  }
]);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);