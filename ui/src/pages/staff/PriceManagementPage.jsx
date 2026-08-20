import React, { useState, useEffect } from 'react';
import { 
  Download, Plus, Eye, ChevronLeft, ChevronRight, 
  Search, Layers, Hourglass, CheckCircle2, XCircle, Loader2, ShieldCheck 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Địa chỉ backend FastAPI của pricing_service
const API_BASE_URL = 'http://localhost:8082/api/v1/price-lists';

export default function PriceManagementPage() {
  const navigate = useNavigate();

  const [stats, setStats] = useState({ total: 0, submitted: 0, approved: 0, effective: 0, rejected: 0 });
  const [priceLists, setPriceLists] = useState([]);
  const [availableCustomers, setAvailableCustomers] = useState(['Tất cả']);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);

  const [activeStatusTab, setActiveStatusTab] = useState('Tất cả');
  const [selectedType, setSelectedType] = useState('Tất cả');
  const [selectedCustomer, setSelectedCustomer] = useState('Tất cả');
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const availableTypes = ['Tất cả', 'CUSTOMER', 'CONTRACT', 'GENERAL', 'SERVICE_GROUP', 'SERVICE_TYPE'];

  // Gọi API lấy số liệu Stat Cards
  useEffect(() => {
    fetch(`${API_BASE_URL}/stats`)
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.error('Lỗi lấy thống kê:', err));
  }, []);

  // Gọi API lấy danh sách Bảng giá
  useEffect(() => {
    setLoading(true);

    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (activeStatusTab !== 'Tất cả') params.append('status', activeStatusTab);
    if (selectedType !== 'Tất cả') params.append('type', selectedType);
    if (selectedCustomer !== 'Tất cả') params.append('customer', selectedCustomer);
    if (searchTerm.trim() !== '') params.append('search', searchTerm.trim());

    fetch(`${API_BASE_URL}?${params.toString()}`)
      .then((res) => res.json())
      .then((data) => {
        setPriceLists(data.items || []);
        setTotalItems(data.total || 0);
        if (data.available_customers) {
          setAvailableCustomers(data.available_customers);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Lỗi lấy danh sách bảng giá:', err);
        setLoading(false);
      });
  }, [activeStatusTab, selectedType, selectedCustomer, searchTerm, page]);

  // Reset về trang 1 khi thay đổi bộ lọc
  const handleFilterChange = (setter, value) => {
    setter(value);
    setPage(1);
  };

  // Helper render Badge trạng thái
  const renderStatusBadge = (status) => {
    const s = (status || '').toUpperCase();
    switch (s) {
      case 'SUBMITTED':
        return <span className="px-2.5 py-0.5 rounded bg-sky-100/70 text-sky-700 text-[10px] font-bold tracking-wide">SUBMITTED</span>;
      case 'APPROVED':
        return <span className="px-2.5 py-0.5 rounded bg-blue-100/70 text-blue-700 text-[10px] font-bold tracking-wide">APPROVED</span>;
      case 'EFFECTIVE':
        return <span className="px-2.5 py-0.5 rounded bg-emerald-100/70 text-emerald-700 text-[10px] font-bold tracking-wide">EFFECTIVE</span>;
      case 'DRAFT':
        return <span className="px-2.5 py-0.5 rounded bg-amber-100/70 text-amber-700 text-[10px] font-bold tracking-wide">DRAFT</span>;
      case 'REJECTED':
        return <span className="px-2.5 py-0.5 rounded bg-rose-100/70 text-rose-700 text-[10px] font-bold tracking-wide">REJECTED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-bold">{s}</span>;
    }
  };

  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  return (
    <div className="space-y-4 text-slate-700 font-sans">
      
      {/* 1. HEADER TRANG & BUTTONS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Quản lý đơn giá</h1>
          <p className="text-xs text-slate-500 mt-1">
            Hệ thống cấu hình đơn giá dịch vụ logistics, quản lý phiên bản hiệu lực và luồng phê duyệt giá.
          </p>
        </div>
        <div className="flex items-center space-x-2.5">
          <button className="px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 shadow-xs flex items-center space-x-1.5 cursor-pointer">
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Xuất Excel</span>
          </button>
          
          <button 
            onClick={() => navigate('/staff/price-lists/create')}
            className="px-4 py-2 rounded-lg bg-[#2b727d] hover:bg-[#235d67] text-xs font-semibold text-white shadow-xs flex items-center space-x-1.5 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Tạo bảng giá mới</span>
          </button>
        </div>
      </div>

      {/* 2. 5 THẺ THỐNG KÊ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Tổng số bảng giá</p>
            <p className="text-xl font-bold text-slate-800 mt-0.5">{stats.total}</p>
          </div>
          <div className="p-2 rounded-lg bg-slate-50 text-slate-400">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Chờ duyệt (SUBMITTED)</p>
            <p className="text-xl font-bold text-amber-600 mt-0.5">{stats.submitted}</p>
          </div>
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
            <Hourglass className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Đã duyệt (APPROVED)</p>
            <p className="text-xl font-bold text-blue-600 mt-0.5">{stats.approved || 0}</p>
          </div>
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Hiệu lực (EFFECTIVE)</p>
            <p className="text-xl font-bold text-emerald-600 mt-0.5">{stats.effective}</p>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Bị từ chối (REJECTED)</p>
            <p className="text-xl font-bold text-rose-600 mt-0.5">{stats.rejected}</p>
          </div>
          <div className="p-2 rounded-lg bg-rose-50 text-rose-600">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 3. BỘ LỌC CÙNG 1 HÀNG NGANG (ĐÃ THU NHỎ 2 Ô ĐẦU TỐI ƯU) */}
      <div className="bg-white p-2.5 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center justify-between gap-2 flex-nowrap overflow-x-auto">
          
          {/* Nhóm dropdown bên trái - Thu nhỏ tối đa */}
          <div className="flex items-center space-x-2 shrink-0">
            <div className="flex items-center space-x-1 bg-slate-50 px-2 py-1 rounded-lg border border-slate-200 text-[11px]">
              <span className="text-slate-500 whitespace-nowrap">Loại:</span>
              <select 
                value={selectedType}
                onChange={(e) => handleFilterChange(setSelectedType, e.target.value)}
                className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer text-[11px] max-w-[110px] truncate"
              >
                {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="flex items-center space-x-1 bg-slate-50 px-2 py-1 rounded-lg border border-slate-200 text-[11px]">
              <span className="text-slate-500 whitespace-nowrap">Khách hàng:</span>
              <select 
                value={selectedCustomer}
                onChange={(e) => handleFilterChange(setSelectedCustomer, e.target.value)}
                className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer max-w-[120px] truncate text-[11px]"
              >
                {availableCustomers.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          {/* Nhóm Tabs & Tìm kiếm bên phải */}
          <div className="flex items-center space-x-2 shrink-0">
            <div className="bg-slate-100/80 p-0.5 rounded-lg flex items-center text-[11px] font-medium text-slate-500">
              {['Tất cả', 'SUBMITTED', 'APPROVED', 'EFFECTIVE', 'DRAFT', 'REJECTED'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => handleFilterChange(setActiveStatusTab, tab)}
                  className={`px-2.5 py-1 rounded-md transition cursor-pointer whitespace-nowrap ${
                    activeStatusTab === tab 
                      ? 'bg-white text-slate-800 shadow-xs font-semibold' 
                      : 'hover:text-slate-800'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Tìm kiếm..."
                value={searchTerm}
                onChange={(e) => handleFilterChange(setSearchTerm, e.target.value)}
                className="pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-[11px] w-36 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
              />
            </div>
          </div>

        </div>
      </div>

      {/* 4. BẢNG DỮ LIỆU */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/50 text-[11px] font-semibold text-slate-500">
                <th className="py-3 px-4">Mã bảng giá</th>
                <th className="py-3 px-4">Tên bảng giá / Đối tượng</th>
                <th className="py-3 px-4">Loại áp dụng</th>
                <th className="py-3 px-4">Phiên bản</th>
                <th className="py-3 px-4">Thời gian hiệu lực</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4">Tạo bởi</th>
                <th className="py-3 px-4 text-center">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Loader2 className="w-6 h-6 animate-spin text-[#2b727d]" />
                      <span>Đang tải dữ liệu từ server...</span>
                    </div>
                  </td>
                </tr>
              ) : priceLists.length > 0 ? (
                priceLists.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/70 transition">
                    <td className="py-3 px-4 font-semibold text-slate-900">{item.id}</td>
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-800">{item.name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{item.contractId}</div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">
                        {item.type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600 font-medium">{item.version}</td>
                    <td className="py-3 px-4 text-slate-600">{item.effectiveTime}</td>
                    <td className="py-3 px-4">{renderStatusBadge(item.status)}</td>
                    <td className="py-3 px-4">
                      <div className="text-slate-800 font-medium">
                        {item.createdBy || 'Admin'}
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {item.createdAt || item.updatedAt}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      <button 
                        onClick={() => navigate(`/staff/price-lists/${item.id}`)}
                        className="p-1 text-slate-400 hover:text-sky-600 rounded transition cursor-pointer"
                        title="Xem chi tiết"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400 text-xs">
                    Không tìm thấy bảng giá phù hợp với bộ lọc.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* 5. PHÂN TRANG */}
        <div className="p-3.5 border-t border-slate-200 bg-white flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div>
            Hiển thị <strong className="text-slate-800 font-semibold">{priceLists.length}</strong> trong tổng số <strong className="text-slate-800 font-semibold">{totalItems}</strong> bảng giá
          </div>
          <div className="flex items-center space-x-1">
            <button 
              disabled={page <= 1}
              onClick={() => setPage(prev => Math.max(prev - 1, 1))}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="px-3 py-1 rounded-lg bg-slate-900 text-white font-semibold text-[11px]">
              {page} / {totalPages}
            </span>
            <button 
              disabled={page >= totalPages}
              onClick={() => setPage(prev => Math.min(prev + 1, totalPages))}
              className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}