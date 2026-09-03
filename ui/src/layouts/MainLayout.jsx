import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';

export default function MainLayout({ user, onLogout }) {
  const location = useLocation();

  // Tự động đổi tiêu đề Header dựa trên đường dẫn URL
  const getHeaderTitle = () => {
    const path = location.pathname;
    if (path === '/') return 'Tổng quan Dashboard';
    if (path.includes('/contracts')) return 'Quản lý hợp đồng';
    if (path.includes('/price-lists')) return 'Quản lý bảng giá';
    if (path.includes('/volumes')) return 'Quản lý sản lượng';
    if (path.includes('/payments')) return 'Quản lý thanh toán';
    if (path.includes('/users')) return 'Quản lý người dùng';
    return 'Trang chủ';
  };

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-700">
      {/* Sidebar bên trái (Truyền prop user để đổi theme) */}
      <Sidebar user={user} onLogout={onLogout} />

      {/* Khu vực nội dung bên phải */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Header title={getHeaderTitle()} user={user} />

        <main className="p-6 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}