import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  FileText, Tag, LineChart, CreditCard, 
  ArrowRight, TrendingUp, Clock, ShieldAlert 
} from 'lucide-react';

export default function HomePage({ user }) {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
      
      {/* 1. Banner Chào Mừng */}
      <div className="bg-gradient-to-r from-slate-900 to-slate-800 rounded-2xl p-6 text-white shadow-md flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold">Xin chào, {user?.email || 'Quản trị viên'} 👋</h2>
          <p className="text-xs text-slate-300 mt-1">
            Chào mừng bạn quay trở lại với Hệ thống Quản trị Kinh doanh ABC Logistics.
          </p>
        </div>
        <div className="hidden sm:block text-right">
          <span className="text-[11px] bg-slate-700/60 px-3 py-1.5 rounded-lg border border-slate-600/50">
            Năm làm việc: <strong className="text-sky-400">2026</strong>
          </span>
        </div>
      </div>

      {/* 2. Lối Tắt Nghiệp Vụ (Đã đổi đường dẫn sang Tiếng Anh) */}
      <div>
        <h3 className="text-sm font-bold text-slate-800 mb-3">Truy cập nhanh nghiệp vụ</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* Quản lý Hợp đồng */}
          <div 
            onClick={() => navigate('/contracts')}
            className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-sky-500 hover:shadow-md transition cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <FileText className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-slate-800 group-hover:text-sky-600 transition flex items-center justify-between">
              <span>Quản lý Hợp đồng</span>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h4>
            <p className="text-xs text-slate-500 mt-1">Tra cứu, tạo mới và quản lý phụ lục hợp đồng khách hàng.</p>
          </div>

          {/* Quản lý Bảng giá */}
          <div 
            onClick={() => navigate('/price-lists')}
            className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-sky-500 hover:shadow-md transition cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <Tag className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-slate-800 group-hover:text-sky-600 transition flex items-center justify-between">
              <span>Quản lý Bảng giá</span>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h4>
            <p className="text-xs text-slate-500 mt-1">Cấu hình biểu giá dịch vụ cảng, kho bãi và phê duyệt.</p>
          </div>

          {/* Quản lý Sản lượng */}
          <div 
            onClick={() => navigate('/volumes')}
            className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-sky-500 hover:shadow-md transition cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <LineChart className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-slate-800 group-hover:text-sky-600 transition flex items-center justify-between">
              <span>Quản lý Sản lượng</span>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h4>
            <p className="text-xs text-slate-500 mt-1">Theo dõi sản lượng container, hàng hóa xuất nhập tồn.</p>
          </div>

          {/* Quản lý Thanh toán */}
          <div 
            onClick={() => navigate('/payments')}
            className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs hover:border-sky-500 hover:shadow-md transition cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center mb-3 group-hover:scale-110 transition">
              <CreditCard className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-slate-800 group-hover:text-sky-600 transition flex items-center justify-between">
              <span>Quản lý Thanh toán</span>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition" />
            </h4>
            <p className="text-xs text-slate-500 mt-1">Đối soát công nợ, hóa đơn và lịch sử thanh toán.</p>
          </div>

        </div>
      </div>

      {/* 3. Các Chỉ Số Thống Kê Tổng Quan */}
      <div>
        <h3 className="text-sm font-bold text-slate-800 mb-3">Tóm tắt hoạt động trong tháng</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Hợp đồng đang chạy</span>
              <FileText className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-slate-800">142</span>
              <span className="text-xs font-semibold text-emerald-600 flex items-center">
                <TrendingUp className="w-3 h-3 mr-0.5" /> +5%
              </span>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Bảng giá chờ duyệt</span>
              <Clock className="w-4 h-4 text-amber-500" />
            </div>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-amber-600">23</span>
              <span className="text-xs text-slate-400">cần xử lý ngay</span>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Sản lượng tháng (TEU)</span>
              <LineChart className="w-4 h-4 text-slate-400" />
            </div>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-slate-800">18,450</span>
              <span className="text-xs font-semibold text-emerald-600 flex items-center">
                <TrendingUp className="w-3 h-3 mr-0.5" /> +12%
              </span>
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 text-xs font-medium">
              <span>Công nợ quá hạn</span>
              <ShieldAlert className="w-4 h-4 text-rose-500" />
            </div>
            <div className="mt-2 flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-rose-600">3.2 tỷ</span>
              <span className="text-xs text-slate-400">4 khách hàng</span>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}