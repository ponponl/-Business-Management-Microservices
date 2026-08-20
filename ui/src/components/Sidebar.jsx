import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FileText, 
  Tag, 
  LineChart, 
  CreditCard, 
  LogOut 
} from 'lucide-react';

const ROLE_SIDEBAR_THEMES = {
  STAFF: {
    subTitle: 'Kinh doanh & Nghiệp vụ',
    activeBg: 'bg-blue-600 text-white shadow-xs',
    subTitleColor: 'text-blue-400',
    borderColor: 'border-blue-500/30'
  },
  MANAGER: {
    subTitle: 'Quản lý & Thẩm định',
    activeBg: 'bg-emerald-600 text-white shadow-xs',
    subTitleColor: 'text-emerald-400',
    borderColor: 'border-emerald-500/30'
  },
  DIRECTOR: {
    subTitle: 'Ban Giám Đốc',
    activeBg: 'bg-amber-500 text-white shadow-xs',
    subTitleColor: 'text-amber-400',
    borderColor: 'border-amber-500/30'
  }
};

export default function Sidebar({ user, onLogout }) {
  const role = user?.role?.toLowerCase() || 'staff';
  const currentTheme = ROLE_SIDEBAR_THEMES[user?.role] || ROLE_SIDEBAR_THEMES.STAFF;

  // Tạo đường dẫn động theo từng Role
  const navItems = [
    { path: `/${role}`, label: 'Tổng quan', icon: LayoutDashboard },
    { path: `/${role}/contracts`, label: 'Quản lý hợp đồng', icon: FileText },
    { path: `/${role}/price-lists`, label: 'Quản lý bảng giá', icon: Tag },
    { path: `/${role}/volumes`, label: 'Quản lý sản lượng', icon: LineChart },
    { path: `/${role}/payments`, label: 'Quản lý thanh toán', icon: CreditCard }
  ];

  return (
    <aside className="w-60 bg-[#1e293b] text-slate-300 flex flex-col min-h-screen select-none">
      {/* Brand Logo */}
      <div className="p-5 border-b border-slate-700/50">
        <h1 className="text-white font-bold text-base tracking-wide flex items-center justify-between">
          ABC Logistics
        </h1>
        <p className={`text-[11px] font-medium mt-0.5 ${currentTheme.subTitleColor}`}>
          {currentTheme.subTitle}
        </p>
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
              end={item.path === `/${role}`}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition ${
                  isActive
                    ? `${currentTheme.activeBg} font-semibold`
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
        <div className={`flex items-center justify-between p-2 rounded-lg bg-slate-800/60 border ${currentTheme.borderColor}`}>
          <div className="truncate pr-2">
            <p className="text-xs font-semibold text-white truncate">{user?.name || 'Người dùng'}</p>
            <p className="text-[10px] text-slate-400 truncate">{user?.email || 'user@abclogistics.vn'}</p>
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