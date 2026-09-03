import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

import MainLayout from './layouts/MainLayout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/HomePage';

// Quản lý bảng giá
import PriceManagementStaff from './pages/staff/PriceManagementPage.jsx';
import CreatePriceListStaff from './pages/staff/CreatePriceListPage.jsx';
import PriceListDetailStaff from './pages/staff/PriceListDetailPage.jsx';
import PriceListHistoryDetail from './pages/PriceListHistoryDetail.jsx';

import PriceListApprovalPage from './pages/manager/PriceListApprovalPage.jsx';
import ContractManagementManagerPage from './pages/manager/ContractManagementPage.jsx';
import ContractReviewPage from './pages/manager/ContractReviewPage.jsx';
import DirectorPriceListApprovalPage from './pages/director/DirectorPriceListApprovalPage.jsx';
import ContractManagementDirectorPage from './pages/director/ContractManagementPage.jsx';
import ContractReviewDirectorPage from './pages/director/ContractReviewPage.jsx';

// Quản lý sản lượng
import ProductionManagementStaffPage from './pages/staff/ProductionManagementPage.jsx';
import ProductionManagementManagerPage from './pages/manager/ProductionManagementPage.jsx';
import ProductionManagementDirectorPage from './pages/director/ProductionManagementPage.jsx';

// Quản lý thanh toán
import PaymentManagementPage from './pages/staff/PaymentManagementPage.jsx';

import ContractManagementStaffPage from './pages/staff/ContractManagementPage.jsx';

const EmptyPage = () => <div className="w-full min-h-[400px] bg-transparent" />;

const IndexRedirect = ({ user }) => {
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={`/${user.role.toLowerCase()}`} replace />;
};

const RoleRoute = ({ user, allowedRoles, children }) => {
  if (!user) return <Navigate to="/login" replace />;
  if (!allowedRoles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
};

export default function App() {
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('user_info');
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const handleLogin = (userData) => {
    const loggedUser = {
      name: userData.username,
      username: userData.username,
      role: userData.role, // "STAFF", "MANAGER", hoặc "DIRECTOR" 
      token: userData.token,
    };

    setUser(loggedUser);
    localStorage.setItem('user_info', JSON.stringify(loggedUser));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user_info');
    localStorage.removeItem('token');
    localStorage.removeItem('user_role');
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<IndexRedirect user={user} />} />
        <Route 
          path="/login" 
          element={user ? <Navigate to="/" replace /> : <LoginPage onLoginSuccess={handleLogin} />} 
        />

        {/* ========================================================= */}
        {/* 1. KHU VỰC NHÂN VIÊN (STAFF)                             */}
        {/* ========================================================= */}
        <Route element={<RoleRoute user={user} allowedRoles={['STAFF']}><MainLayout user={user} onLogout={handleLogout} /></RoleRoute>}>
          <Route path="/staff" element={<DashboardPage user={user} />} />

          {/* SERVICE: QUẢN LÝ BẢNG GIÁ */}
          <Route path="/staff/price-lists" element={<PriceManagementStaff user={user} />} />
          <Route path="/staff/price-lists/create" element={<CreatePriceListStaff user={user} />} />
          <Route path="/staff/price-lists/:id" element={<PriceListDetailStaff user={user} />} />
          <Route path="/staff/price-lists/:id/versions" element={<PriceListHistoryDetail user={user} />} />

          {/* SERVICE KHÁC */}
          <Route path="/staff/contracts" element={<ContractManagementStaffPage user={user} />} />
          <Route path="/staff/volumes" element={<ProductionManagementStaffPage user={user} />} />
          <Route path="/staff/payments" element={<PaymentManagementPage user={user} />} />
        </Route>

        {/* ========================================================= */}
        {/* 2. KHU VỰC QUẢN LÝ (MANAGER)                             */}
        {/* ========================================================= */}
        <Route element={<RoleRoute user={user} allowedRoles={['MANAGER']}><MainLayout user={user} onLogout={handleLogout} /></RoleRoute>}>
          <Route path="/manager" element={<DashboardPage user={user} />} />

          {/* SERVICE: QUẢN LÝ BẢNG GIÁ */}
          <Route path="/manager/price-lists" element={<PriceListApprovalPage user={user} />} />
          <Route path="/manager/price-lists/:id/versions" element={<PriceListHistoryDetail user={user} />} />

          {/* SERVICE KHÁC */}
          <Route path="/manager/contracts" element={<ContractManagementManagerPage user={user} />} />
          <Route path="/manager/contracts/review" element={<ContractReviewPage user={user} />} />
          <Route path="/manager/volumes" element={<ProductionManagementManagerPage user={user} />} />
          <Route path="/manager/payments" element={<PaymentManagementPage user={user} />} />
        </Route>

        {/* ========================================================= */}
        {/* 3. KHU VỰC GIÁM ĐỐC (DIRECTOR)                            */}
        {/* ========================================================= */}
        <Route element={<RoleRoute user={user} allowedRoles={['DIRECTOR']}><MainLayout user={user} onLogout={handleLogout} /></RoleRoute>}>
          <Route path="/director" element={<DashboardPage user={user} />} />

          {/* SERVICE: QUẢN LÝ BẢNG GIÁ */}
          <Route path="/director/price-lists" element={<DirectorPriceListApprovalPage user={user} />} />
          <Route path="/director/price-lists/:id/versions" element={<PriceListHistoryDetail user={user} />} />

          {/* SERVICE KHÁC */}
          <Route path="/director/contracts" element={<ContractManagementDirectorPage user={user} />} />
          <Route path="/director/contracts/review" element={<ContractReviewDirectorPage user={user} />} />
          <Route path="/director/volumes" element={<ProductionManagementDirectorPage user={user} />} />
          <Route path="/director/payments" element={<PaymentManagementPage user={user} />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}