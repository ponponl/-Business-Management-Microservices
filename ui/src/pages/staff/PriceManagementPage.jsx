import React, { useState, useEffect } from 'react';
import { 
  Download, Plus, Eye, ChevronLeft, ChevronRight, 
  Search, Layers, Hourglass, CheckCircle2, XCircle, Loader2 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Địa chỉ backend FastAPI của pricing_service
const API_BASE_URL = 'http://localhost:8082/api/v1/price-lists';

export default function PriceManagementPage() {
  const navigate = useNavigate();

  const [stats, setStats] = useState({ total: 0, submitted: 0, effective: 0, rejected: 0 });
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

  // Gọi API lấy số liệu 4 Stat Cards (Chạy 1 lần khi load trang)
  useEffect(() => {
    fetch(`${API_BASE_URL}/stats`)
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch((err) => console.error('Lỗi lấy thống kê:', err));
  }, []);

  // Gọi API lấy danh sách Bảng giá (Chạy khi Bộ lọc hoặc Trang đổi)
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
    switch (status) {
      case 'SUBMITTED':
        return <span className="px-2.5 py-0.5 rounded bg-sky-100/70 text-sky-700 text-[10px] font-bold tracking-wide">SUBMITTED</span>;
      case 'EFFECTIVE':
        return <span className="px-2.5 py-0.5 rounded bg-emerald-100/70 text-emerald-700 text-[10px] font-bold tracking-wide">EFFECTIVE</span>;
      case 'DRAFT':
        return <span className="px-2.5 py-0.5 rounded bg-amber-100/70 text-amber-700 text-[10px] font-bold tracking-wide">DRAFT</span>;
      case 'REJECTED':
        return <span className="px-2.5 py-0.5 rounded bg-rose-100/70 text-rose-700 text-[10px] font-bold tracking-wide">REJECTED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-bold">{status}</span>;
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
          
          {/* SỬA ĐƯỜNG DẪN TẠO BẢNG GIÁ MỚI */}
          <button 
            onClick={() => navigate('/staff/price-lists/create')}
            className="px-4 py-2 rounded-lg bg-[#2b727d] hover:bg-[#235d67] text-xs font-semibold text-white shadow-xs flex items-center space-x-1.5 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Tạo bảng giá mới</span>
          </button>
        </div>
      </div>

      {/* 2. 4 THẺ THỐNG KÊ (STAT CARDS REFRESH DỮ LIỆU THẬT) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
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

      {/* 3. BỘ LỌC VÀ BẢNG TÌM KIẾM */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
              <span className="text-slate-500">Loại áp dụng:</span>
              <select 
                value={selectedType}
                onChange={(e) => handleFilterChange(setSelectedType, e.target.value)}
                className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer"
              >
                {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
              <span className="text-slate-500">Khách hàng:</span>
              <select 
                value={selectedCustomer}
                onChange={(e) => handleFilterChange(setSelectedCustomer, e.target.value)}
                className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer max-w-[150px] truncate"
              >
                {availableCustomers.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="bg-slate-100/80 p-0.5 rounded-lg flex items-center text-[11px] font-medium text-slate-500">
              {['Tất cả', 'EFFECTIVE', 'SUBMITTED', 'DRAFT', 'REJECTED'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => handleFilterChange(setActiveStatusTab, tab)}
                  className={`px-3 py-1 rounded-md transition cursor-pointer ${
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
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Tìm kiếm..."
                value={searchTerm}
                onChange={(e) => handleFilterChange(setSearchTerm, e.target.value)}
                className="pl-8 pr-3 py-1 rounded-lg border border-slate-200 text-xs w-48 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
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
                <th className="py-3 px-4">Cập nhật</th>
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
                      <div className="text-slate-800 font-medium">{item.updatedBy}</div>
                      <div className="text-[10px] text-slate-400">{item.updatedAt}</div>
                    </td>
                    <td className="py-3 px-4 text-center">
                      {/* SỬA ĐƯỜNG DẪN XEM CHI TIẾT */}
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

        {/* 5. PHÂN TRANG THỰC TẾ */}
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