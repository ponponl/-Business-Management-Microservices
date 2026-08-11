import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, Tag, LineChart, CreditCard, LogOut } from 'lucide-react';

export default function Sidebar({ user, onLogout }) {
  const navItems = [
    { path: '/', label: 'Tổng quan', icon: LayoutDashboard },
    { path: '/contracts', label: 'Quản lý hợp đồng', icon: FileText },
    { path: '/price-lists', label: 'Quản lý bảng giá', icon: Tag },
    { path: '/volumes', label: 'Quản lý sản lượng', icon: LineChart },
    { path: '/payments', label: 'Quản lý thanh toán', icon: CreditCard },
  ];

  return (
    <aside className="w-60 bg-[#1e293b] text-slate-300 flex flex-col min-h-screen">
      {/* Brand Logo */}
      <div className="p-5 border-b border-slate-700/50">
        <h1 className="text-white font-bold text-base tracking-wide">ABC Logistics</h1>
        <p className="text-[11px] text-slate-400 mt-0.5">Quản trị kinh doanh</p>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 p-3 space-y-1">
        <p className="px-3 text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Nghiệp vụ
        </p>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                  isActive
                    ? 'bg-sky-600 text-white shadow-xs'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* User info & Logout */}
      <div className="p-3 border-t border-slate-700/50">
        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-800/60">
          <div className="truncate pr-2">
            <p className="text-xs font-semibold text-white truncate">{user?.name || 'Nguyễn Văn A'}</p>
            <p className="text-[10px] text-slate-400 truncate">{user?.email || 'admin@abclogistics.vn'}</p>
          </div>
          <button 
            onClick={onLogout}
            title="Đăng xuất"
            className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700/50 rounded-md transition cursor-pointer"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}