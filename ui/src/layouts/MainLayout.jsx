import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import Header from '../components/Header';

export default function MainLayout({ user, onLogout }) {
  const location = useLocation();

  // Tự động đổi tiêu đề Header dựa trên đường dẫn URL (Path)
  const getHeaderTitle = () => {
    switch (location.pathname) {
      case '/': return 'Tổng quan Dashboard';
      case '/hop-dong': return 'Quản lý hợp đồng';
      case '/bang-gia': return 'Quản lý bảng giá';
      case '/san-luong': return 'Quản lý sản lượng';
      case '/thanh-toan': return 'Quản lý thanh toán';
      default: return 'Trang chủ';
    }
  };

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-700">
      {/* Sidebar bên trái */}
      <Sidebar user={user} onLogout={onLogout} />

      {/* Khu vực bên phải */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <Header title={getHeaderTitle()} />

        {/* <Outlet /> là nơi các trang con (Dashboard, Bảng giá,...) hiển thị */}
        <main className="p-6 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}