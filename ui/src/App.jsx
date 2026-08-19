import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';

// Layouts & Authentication
import MainLayout from './layouts/MainLayout';
import LoginPage from './pages/LoginPage';

// Các trang
import DashboardPage from './pages/HomePage';

// Các trang Quản lý Giá 
import PriceManagementPage from './pages/PriceManagementPage.jsx';
import CreatePriceListPage from './pages/CreatePriceListPage.jsx';
import PriceListDetailPage from './pages/PriceListDetailPage.jsx';



// Component cho các trang chưa làm
const PagePlaceholder = ({ title }) => (
  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
    <h2 className="text-base font-bold text-slate-800">{title}</h2>
    <p className="text-xs text-slate-500 mt-1">Trang này chưa được khởi tạo component.</p>
  </div>
);

// Component Bảo vệ Route
const ProtectedRoute = ({ user, children }) => {
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

export default function App() {
  const [user, setUser] = useState(null);

  const handleLogin = (userData) => {
    setUser({
      name: userData.name || 'Nguyễn Văn A',
      email: userData.email || 'a.nguyen@abc.com',
    });
  };

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <BrowserRouter>
      <Routes>
        {/* 1. TRANG ĐĂNG NHẬP */}
        <Route 
          path="/login" 
          element={
            user ? <Navigate to="/" replace /> : <LoginPage onLoginSuccess={handleLogin} />
          } 
        />

        {/* 2. KHU VỰC ĐÃ ĐĂNG NHẬP (NESTED ROUTES IN MAINLAYOUT) */}
        <Route 
          path="/" 
          element={
            <ProtectedRoute user={user}>
              <MainLayout user={user} onLogout={handleLogout} />
            </ProtectedRoute>
          }
        >
          {/* Trang chủ / Dashboard */}
          <Route index element={<DashboardPage user={user} />} />

          {/* SERVICE 1: PRICE LISTS (BẢNG GIÁ) */}
          <Route path="price-lists" element={<PriceManagementPage />} />
          <Route path="price-lists/create" element={<CreatePriceListPage />} />
          <Route path="price-lists/:id" element={<PriceListDetailPage />} />

          {/* SERVICE 2: CONTRACTS (HỢP ĐỒNG) */}
          <Route path="contracts" element={<PagePlaceholder title="Quản lý Hợp đồng" />} />

          {/* SERVICE 3: VOLUMES (SẢN LƯỢNG) */}
          <Route path="volumes" element={<PagePlaceholder title="Quản lý Sản lượng" />} />

          {/* SERVICE 4: PAYMENTS (THANH TOÁN) */}
          <Route path="payments" element={<PagePlaceholder title="Quản lý Thanh toán" />} />

          {/* Catch-all Route */}
          <Route path="*" element={<Navigate to="/" replace />} />

        </Route>
      </Routes>
    </BrowserRouter>
  );
}