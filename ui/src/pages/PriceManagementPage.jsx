import React, { useState, useMemo } from 'react';
import { 
  Download, Plus, Eye, ChevronLeft, ChevronRight, 
  Search, Layers, Hourglass, CheckCircle2, XCircle 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function PriceManagementPage() {
  const navigate = useNavigate();

  const [activeStatusTab, setActiveStatusTab] = useState('Tất cả');
  const [selectedType, setSelectedType] = useState('Tất cả');
  const [selectedCustomer, setSelectedCustomer] = useState('Tất cả');
  const [searchTerm, setSearchTerm] = useState('');

  const priceLists = [
    {
      id: 'PL-2026-001',
      name: 'Cảng Cát Lái',
      contractId: 'HD-2025-0089',
      type: 'CUSTOMER',
      version: 'v3.0',
      effectiveTime: '01/01/2026 - 31/12/2026',
      status: 'SUBMITTED',
      updatedBy: 'Ban Giám đốc',
      updatedAt: '08/07/2026 14:22'
    },
    {
      id: 'PL-2026-002',
      name: 'Công ty CP XNK Đại Dương',
      contractId: 'HD-2025-0076',
      type: 'CONTRACT',
      version: 'v1.0',
      effectiveTime: '01/06/2026 - 30/06/2027',
      status: 'DRAFT',
      updatedBy: 'Phòng Pháp chế',
      updatedAt: '05/07/2026 10:05'
    },
    {
      id: 'PL-2026-003',
      name: 'Cảng Cái Mép Thị Vải',
      contractId: 'HD-2024-0132',
      type: 'GENERAL',
      version: 'v2.1',
      effectiveTime: '01/06/2026 - 30/06/2026',
      status: 'EFFECTIVE',
      updatedBy: 'Trần Văn B',
      updatedAt: '05/07/2026 09:40'
    },
    {
      id: 'PL-2026-004',
      name: 'Cty TNHH Vận tải Phương Nam',
      contractId: 'HD-2025-0054',
      type: 'CUSTOMER',
      version: 'v1.2',
      effectiveTime: '01/06/2026 - 30/06/2026',
      status: 'REJECTED',
      updatedBy: 'Trần Văn B',
      updatedAt: '04/07/2026 16:51'
    },
    {
      id: 'PL-2026-005',
      name: 'Cảng Cát Lái',
      contractId: 'HD-2025-0089',
      type: 'CUSTOMER',
      version: 'v2.0',
      effectiveTime: '01/05/2026 - 31/05/2026',
      status: 'EFFECTIVE',
      updatedBy: 'Nguyễn Văn A',
      updatedAt: '03/07/2026 08:12'
    },
    {
      id: 'PL-2026-006',
      name: 'Tập đoàn Hòa Phát',
      contractId: 'HD-2026-0112',
      type: 'SERVICE_GROUP',
      version: 'v1.0',
      effectiveTime: '15/06/2026 - 15/06/2027',
      status: 'SUBMITTED',
      updatedBy: 'Trần Văn B',
      updatedAt: '02/07/2026 17:00'
    },
    {
      id: 'PL-2026-007',
      name: 'Kho vận Gemadept',
      contractId: 'HD-2024-0095',
      type: 'SERVICE_TYPE',
      version: 'v4.2',
      effectiveTime: '01/01/2026 - 31/12/2026',
      status: 'EFFECTIVE',
      updatedBy: 'Nguyễn Văn A',
      updatedAt: '01/07/2026 11:30'
    },
    {
      id: 'PL-2026-008',
      name: 'Logistics TTC',
      contractId: 'HD-2025-0034',
      type: 'CUSTOMER',
      version: 'v1.1',
      effectiveTime: '01/07/2026 - 31/12/2026',
      status: 'DRAFT',
      updatedBy: 'Phòng Kế Hoạch',
      updatedAt: '30/06/2026 09:15'
    },
    {
      id: 'PL-2026-009',
      name: 'Cảng Quốc Tế Tân Cảng',
      contractId: 'HD-2026-0021',
      type: 'CONTRACT',
      version: 'v2.0',
      effectiveTime: '20/06/2026 - 20/06/2027',
      status: 'SUBMITTED',
      updatedBy: 'Trần Văn B',
      updatedAt: '29/06/2026 14:00'
    },
    {
      id: 'PL-2026-010',
      name: 'Tổng kho Vĩnh Long',
      contractId: 'HD-2025-0067',
      type: 'GENERAL',
      version: 'v1.0',
      effectiveTime: '01/01/2026 - 31/12/2026',
      status: 'EFFECTIVE',
      updatedBy: 'Nguyễn Văn A',
      updatedAt: '28/06/2026 10:45'
    },
    {
      id: 'PL-2026-011',
      name: 'Vận Tải Phương Hoàng',
      contractId: 'HD-2025-0104',
      type: 'CUSTOMER',
      version: 'v1.3',
      effectiveTime: '01/03/2026 - 31/12/2026',
      status: 'REJECTED',
      updatedBy: 'Trần Văn B',
      updatedAt: '25/06/2026 16:20'
    }
  ];

  // Danh sách gợi ý Dropdown
  const availableTypes = ['Tất cả', 'CUSTOMER', 'CONTRACT', 'GENERAL', 'SERVICE_GROUP', 'SERVICE_TYPE'];
  const availableCustomers = useMemo(() => {
    const names = Array.from(new Set(priceLists.map(i => i.name)));
    return ['Tất cả', ...names];
  }, [priceLists]);

  // LOGIC LỌC DỮ LIỆU TỰ ĐỘNG
  const filteredData = useMemo(() => {
    return priceLists.filter((item) => {
      const matchStatus = activeStatusTab === 'Tất cả' || item.status === activeStatusTab;
      const matchType = selectedType === 'Tất cả' || item.type === selectedType;
      const matchCustomer = selectedCustomer === 'Tất cả' || item.name === selectedCustomer;
      const term = searchTerm.toLowerCase().trim();
      const matchSearch = !term || 
        item.id.toLowerCase().includes(term) || 
        item.name.toLowerCase().includes(term) ||
        item.contractId.toLowerCase().includes(term);

      return matchStatus && matchType && matchCustomer && matchSearch;
    });
  }, [activeStatusTab, selectedType, selectedCustomer, searchTerm, priceLists]);

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
        return null;
    }
  };

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
            onClick={() => navigate('/price-lists/create')}
            className="px-4 py-2 rounded-lg bg-[#2b727d] hover:bg-[#235d67] text-xs font-semibold text-white shadow-xs flex items-center space-x-1.5 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Tạo bảng giá mới</span>
          </button>
        </div>
      </div>

      {/* 2. 4 THẺ THỐNG KÊ (STAT CARDS) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Tổng số bảng giá</p>
            <p className="text-xl font-bold text-slate-800 mt-0.5">128</p>
          </div>
          <div className="p-2 rounded-lg bg-slate-50 text-slate-400">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Chờ duyệt (SUBMITTED)</p>
            <p className="text-xl font-bold text-amber-600 mt-0.5">23</p>
          </div>
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
            <Hourglass className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Hiệu lực (EFFECTIVE)</p>
            <p className="text-xl font-bold text-emerald-600 mt-0.5">86</p>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Bị từ chối (REJECTED)</p>
            <p className="text-xl font-bold text-rose-600 mt-0.5">19</p>
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
                onChange={(e) => setSelectedType(e.target.value)}
                className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer"
              >
                {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>

            <div className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
              <span className="text-slate-500">Khách hàng:</span>
              <select 
                value={selectedCustomer}
                onChange={(e) => setSelectedCustomer(e.target.value)}
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
                  onClick={() => setActiveStatusTab(tab)}
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
                onChange={(e) => setSearchTerm(e.target.value)}
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
              {filteredData.length > 0 ? (
                filteredData.map((item) => (
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
                      {/* BẤM VÀO CON MẮT SẼ SANG TRANG CHI TIẾT BẢNG GIÁ */}
                      <button 
                        onClick={() => navigate('/price-lists/detail')}
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
            Hiển thị <strong className="text-slate-800 font-semibold">{filteredData.length}</strong> trong tổng số <strong className="text-slate-800 font-semibold">{priceLists.length}</strong> bảng giá
          </div>
          <div className="flex items-center space-x-1">
            <button className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-400 disabled:opacity-50 cursor-pointer">
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <button className="w-7 h-7 rounded-lg bg-slate-900 text-white font-semibold text-[11px] flex items-center justify-center">
              1
            </button>
            <button className="p-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 cursor-pointer">
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

      </div>

    </div>
  );
}