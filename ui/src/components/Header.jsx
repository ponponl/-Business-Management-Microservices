import React, { useState, useEffect, useRef } from 'react';
import { Bell, CheckCircle, XCircle, Info, Package } from 'lucide-react';

const ROLE_HEADER_THEMES = {
  STAFF: { avatarBg: 'bg-blue-600', badgeText: 'Nhân viên', badgeBg: 'bg-blue-50 text-blue-700 border-blue-200' },
  MANAGER: { avatarBg: 'bg-emerald-600', badgeText: 'Quản lý', badgeBg: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  DIRECTOR: { avatarBg: 'bg-amber-500', badgeText: 'Giám đốc', badgeBg: 'bg-amber-50 text-amber-700 border-amber-200' },
};

export default function Header({ title, user }) {
  const currentTheme = ROLE_HEADER_THEMES[user?.role] || ROLE_HEADER_THEMES.STAFF;
  const firstLetter = user?.name ? user.name.charAt(0).toUpperCase() : 'U';

  const [notifications, setNotifications] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const dropdownRef = useRef(null);

  // Lấy dữ liệu thông báo
  const fetchNotifications = async () => {
    try {
      const userId = user?.id || 1;
      const res = await fetch(`http://localhost:8087/api/v1/notifications/?user_id=${userId}`);
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
        setUnreadCount(data.filter(n => !n.is_read).length);
      }
    } catch (error) {
      console.error("Error fetching notifications", error);
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000);
    return () => clearInterval(interval);
  }, [user]);

  // Đóng dropdown khi click ra ngoài
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getIconForEventType = (type) => {
    switch (type) {
      case 'CONTRACT_APPROVED': return <CheckCircle className="w-5 h-5 text-emerald-500" />;
      case 'CONTRACT_REJECTED': return <XCircle className="w-5 h-5 text-red-500" />;
      case 'CONTRACT_CREATED': return <Info className="w-5 h-5 text-blue-500" />;
      case 'VOLUME_RECORDED': return <Package className="w-5 h-5 text-indigo-500" />;
      default: return <Bell className="w-5 h-5 text-slate-400" />;
    }
  };

  const formatDate = (dateString) => {
    const d = new Date(dateString);
    return d.toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
  };

  const handleMarkAllAsRead = async () => {
    try {
      const userId = user?.id || 1;
      await fetch(`http://localhost:8087/api/v1/notifications/read-all?user_id=${userId}`, { method: 'PUT' });
      fetchNotifications();
    } catch (error) {
      console.error("Error marking as read", error);
    }
  };

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
        <div className="relative" ref={dropdownRef}>
          <button 
            onClick={() => {
              setShowDropdown(!showDropdown);
              if (!showDropdown) fetchNotifications(); // Fetch khi mở ra
            }}
            className="w-8 h-8 rounded-lg border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50 relative cursor-pointer transition-colors"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="w-2 h-2 bg-amber-500 rounded-full absolute top-1.5 right-1.5 ring-2 ring-white"></span>
            )}
          </button>

          {/* Notification Dropdown */}
          {showDropdown && (
            <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 shadow-xl rounded-xl overflow-hidden z-50">
              <div className="px-4 py-3 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                <h3 className="font-semibold text-sm text-slate-800">Thông báo</h3>
                {unreadCount > 0 && (
                  <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-semibold">
                    {unreadCount} mới
                  </span>
                )}
              </div>
              
              <div className="max-h-[400px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-8 text-center flex flex-col items-center justify-center text-slate-400">
                    <Bell className="w-8 h-8 text-slate-200 mb-2" />
                    <p className="text-sm">Không có thông báo nào.</p>
                  </div>
                ) : (
                  notifications.map(notif => (
                    <div 
                      key={notif.id} 
                      className={`p-4 border-b border-slate-100 hover:bg-slate-50 transition-colors flex gap-3 ${!notif.is_read ? 'bg-blue-50/30' : ''}`}
                    >
                      <div className="mt-0.5">
                        {getIconForEventType(notif.event_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start mb-1">
                          <p className={`text-sm ${!notif.is_read ? 'font-semibold text-slate-800' : 'font-medium text-slate-700'}`}>
                            {notif.title}
                          </p>
                          <span className="text-[10px] text-slate-400 whitespace-nowrap ml-2">
                            {formatDate(notif.created_at)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 leading-relaxed">
                          {notif.message}
                        </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              {notifications.length > 0 && (
                <div className="p-2 border-t border-slate-100 text-center bg-slate-50/50">
                  <button 
                    onClick={handleMarkAllAsRead}
                    className="text-[11px] text-blue-600 font-semibold hover:text-blue-800 transition-colors w-full py-1.5 rounded-lg hover:bg-blue-50"
                  >
                    Đánh dấu tất cả đã đọc
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* User Avatar */}
        <div className={`w-8 h-8 rounded-lg ${currentTheme.avatarBg} text-white font-semibold text-xs flex items-center justify-center shadow-xs cursor-pointer hover:opacity-90 transition-opacity`}>
          {firstLetter}
        </div>
      </div>
    </header>
  );
}