import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ShieldCheck, 
  Tag, 
  FileText, 
  TrendingUp, 
  CreditCard, 
  Users, 
  ArrowRight, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  Layers 
} from 'lucide-react';

export default function AdminDashboardPage({ user }) {
  const navigate = useNavigate();

  return (
    <div className="space-y-6 font-sans text-slate-700 max-w-7xl mx-auto">
      
      {/* 1. WELCOME BANNER */}
      <div className="bg-slate-900 p-6 rounded-2xl text-white shadow-lg border border-slate-800 flex items-center justify-between">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-6 h-6 text-amber-400" />
            <h1 className="text-xl font-bold">
              Xin chào, <span className="text-amber-300">{user?.email || 'admin@abclogistics.vn'}</span> 👋
            </h1>
          </div>
          <p className="text-xs text-slate-400">
            Chào mừng bạn trở lại với Trung tâm Điều hành & Phê duyệt Quản trị ABC Logistics.
          </p>
        </div>
        <div className="hidden sm:block text-right">
          <span className="inline-block bg-slate-800 text-amber-400 text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-700">
            Năm làm việc: 2026
          </span>
        </div>
      </div>

      {/* 2. TÓM TẮT CHỈ SỐ KPI TOÀN HỆ THỐNG */}
      <div>
        <h2 className="text-sm font-bold text-slate-800 mb-3">Chỉ số giám sát hệ thống</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Bảng giá chờ duyệt</p>
              <div className="flex items-baseline space-x-2 mt-1">
                <span className="text-2xl font-bold text-amber-600">23</span>
                <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                  Cần xử lý
                </span>
              </div>
            </div>
            <div className="p-2.5 bg-amber-50 rounded-xl text-amber-600 border border-amber-100">
              <Clock className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Bảng giá có hiệu lực</p>
              <div className="flex items-baseline space-x-2 mt-1">
                <span className="text-2xl font-bold text-emerald-600">48</span>
                <span className="text-xs text-slate-400 font-medium">đã duyệt</span>
              </div>
            </div>
            <div className="p-2.5 bg-emerald-50 rounded-xl text-emerald-600 border border-emerald-100">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Bảng giá từ chối</p>
              <div className="flex items-baseline space-x-2 mt-1">
                <span className="text-2xl font-bold text-rose-600">5</span>
                <span className="text-xs text-slate-400 font-medium">yêu cầu sửa</span>
              </div>
            </div>
            <div className="p-2.5 bg-rose-50 rounded-xl text-rose-600 border border-rose-100">
              <XCircle className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-400 font-medium">Tổng tài khoản hệ thống</p>
              <div className="flex items-baseline space-x-2 mt-1">
                <span className="text-2xl font-bold text-blue-600">12</span>
                <span className="text-xs text-slate-400 font-medium">nhân sự</span>
              </div>
            </div>
            <div className="p-2.5 bg-blue-50 rounded-xl text-blue-600 border border-blue-100">
              <Users className="w-5 h-5" />
            </div>
          </div>

        </div>
      </div>

      {/* 3. TRUY CẬP NHANH CÁC DỊCH VỤ QUẢN TRỊ */}
      <div>
        <h2 className="text-sm font-bold text-slate-800 mb-3">Truy cập nhanh danh mục nghiệp vụ</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          
          {/* Card 1: Quản lý Bảng giá (Chức năng cốt lõi) */}
          <div 
            onClick={() => navigate('/admin/approvals')}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-blue-500 cursor-pointer transition group flex flex-col justify-between"
          >
            <div className="flex items-start justify-between">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-xl border border-blue-100">
                <Tag className="w-6 h-6" />
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-blue-600 group-hover:translate-x-1 transition" />
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-slate-800 group-hover:text-blue-600">
                Quản lý Bảng giá
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Thẩm định, xem xét và phê duyệt hoặc từ chối các đề xuất bảng giá dịch vụ logistics.
              </p>
            </div>
          </div>

          {/* Card 2: Quản lý Hợp đồng */}
          <div 
            onClick={() => navigate('/admin/contracts')}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-blue-500 cursor-pointer transition group flex flex-col justify-between"
          >
            <div className="flex items-start justify-between">
              <div className="p-3 bg-indigo-50 text-indigo-600 rounded-xl border border-indigo-100">
                <FileText className="w-6 h-6" />
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 group-hover:translate-x-1 transition" />
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-slate-800 group-hover:text-indigo-600">
                Quản lý Hợp đồng
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Giám sát tình trạng ký kết hợp đồng khách hàng, đối tác và điều khoản liên quan.
              </p>
            </div>
          </div>

          {/* Card 3: Quản lý Sản lượng */}
          <div 
            onClick={() => navigate('/admin/volume')}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-blue-500 cursor-pointer transition group flex flex-col justify-between"
          >
            <div className="flex items-start justify-between">
              <div className="p-3 bg-emerald-50 text-emerald-600 rounded-xl border border-emerald-100">
                <TrendingUp className="w-6 h-6" />
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600 group-hover:translate-x-1 transition" />
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-slate-800 group-hover:text-emerald-600">
                Quản lý Sản lượng
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Theo dõi tổng dung lượng giao dịch, sản lượng container và khối lượng vận chuyển.
              </p>
            </div>
          </div>

          {/* Card 4: Quản lý Thanh toán */}
          <div 
            onClick={() => navigate('/admin/payments')}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-blue-500 cursor-pointer transition group flex flex-col justify-between"
          >
            <div className="flex items-start justify-between">
              <div className="p-3 bg-amber-50 text-amber-600 rounded-xl border border-amber-100">
                <CreditCard className="w-6 h-6" />
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-amber-600 group-hover:translate-x-1 transition" />
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-slate-800 group-hover:text-amber-600">
                Quản lý Thanh toán
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Kiểm soát dòng tiền, công nợ khách hàng và trạng thái quyết toán hóa đơn dịch vụ.
              </p>
            </div>
          </div>

          {/* Card 5: Quản lý Người dùng */}
          <div 
            onClick={() => navigate('/admin/users')}
            className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-blue-500 cursor-pointer transition group flex flex-col justify-between"
          >
            <div className="flex items-start justify-between">
              <div className="p-3 bg-purple-50 text-purple-600 rounded-xl border border-purple-100">
                <Users className="w-6 h-6" />
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-purple-600 group-hover:translate-x-1 transition" />
            </div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-slate-800 group-hover:text-purple-600">
                Quản lý Người dùng
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                Cấp tài khoản, phân quyền truy cập hệ thống và quản trị danh sách nhân sự.
              </p>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}