import React from 'react';
import { Bell } from 'lucide-react';

const ROLE_HEADER_THEMES = {
  STAFF: { avatarBg: 'bg-blue-600', badgeText: 'Nhân viên', badgeBg: 'bg-blue-50 text-blue-700 border-blue-200' },
  MANAGER: { avatarBg: 'bg-emerald-600', badgeText: 'Quản lý', badgeBg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  DIRECTOR: { avatarBg: 'bg-amber-500', badgeText: 'Giám đốc', badgeBg: 'bg-amber-50 text-amber-700 border-amber-200' },
};

export default function Header({ title, user }) {
  const currentTheme = ROLE_HEADER_THEMES[user?.role] || ROLE_HEADER_THEMES.STAFF;
  const firstLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'U';

  return (
    <header className="bg-white border-b border-slate-200 h-13 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
      <div className="text-xs text-slate-500">
        Nghiệp vụ / <span className="text-slate-800 font-semibold">{title}</span>
      </div>

      <div className="flex items-center space-x-3">
        {/* Role Badge */}
        <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${currentTheme.badgeBg}`}>
          {currentTheme.badgeText}
        </span>

        {/* Bell Notification */}
        <button className="w-8 h-8 rounded-lg border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50 relative cursor-pointer">
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 bg-amber-500 rounded-full absolute top-1.5 right-1.5"></span>
        </button>

        {/* User Avatar */}
        <div className={`w-8 h-8 rounded-lg ${currentTheme.avatarBg} text-white font-semibold text-xs flex items-center justify-center shadow-xs`}>
          {firstLetter}
        </div>
      </div>
    </header>
  );
}