import React, { useState, useEffect, useCallback } from 'react';
import { 
  Layers, Hourglass, CheckCircle2, XCircle, Eye, Search, 
  Download, Check, X, AlertCircle, Loader2,
  ChevronLeft, ChevronRight, Calendar, ShieldCheck
} from 'lucide-react';

const PRICE_LIST_API = 'http://localhost:8082/api/v1/price-lists';
const APPROVAL_API = 'http://localhost:8082/api/v1/approvals';

export default function PriceListApprovalPage({ user }) {
  // Stats Card State
  const [stats, setStats] = useState({ total: 0, submitted: 0, approved: 0, effective: 0, rejected: 0 });

  // List Data State
  const [priceLists, setPriceLists] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [, setError] = useState(null);

  // Filters State
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Pagination State
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Modals State
  const [selectedItem, setSelectedItem] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [rejectModal, setRejectModal] = useState({ isOpen: false, item: null, reason: '' });
  const [modalConfig, setModalConfig] = useState({
    isOpen: false,
    type: '',
    title: '',
    message: ''
  });

  const getItemCode = (item) => {
    return (
      item?.price_code || 
      item?.priceCode || 
      item?.priceListId || 
      item?.price_list_id || 
      item?.code || 
      item?.id
    );
  };

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${PRICE_LIST_API}/stats`);
      if (!res.ok) throw new Error('Không thể tải thống kê');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Lỗi lấy thống kê:', err);
    }
  }, []);

  const fetchPriceLists = useCallback(async () => {
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (statusFilter !== 'ALL') params.append('status', statusFilter);
    if (typeFilter !== 'ALL') params.append('type', typeFilter);
    if (searchTerm.trim() !== '') params.append('search', searchTerm.trim());

    try {
      const res = await fetch(`${APPROVAL_API}?${params.toString()}`);
      if (!res.ok) throw new Error(`Lỗi kết nối API (${res.status})`);
      const data = await res.json();

      let rawList = [];
      let total = 0;

      if (Array.isArray(data)) {
        rawList = data;
        total = data.length;
      } else {
        rawList = data.items || data.data || [];
        total = data.total || data.total_items || rawList.length;
      }

      setTotalItems(total);

      if (rawList.length > pageSize) {
        const startIndex = (page - 1) * pageSize;
        setPriceLists(rawList.slice(startIndex, startIndex + pageSize));
      } else {
        setPriceLists(rawList);
      }
    } catch (err) {
      console.error('Lỗi tải bảng giá:', err);
      setError(err.message);
      setPriceLists([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter, typeFilter, searchTerm]);

  const handleOpenDetail = async (item) => {
    const code = getItemCode(item);
    if (!code) return;
    
    setModalLoading(true);
    setSelectedItem(item);

    try {
      const res = await fetch(`${PRICE_LIST_API}/${code}`);
      const fullData = res.ok ? await res.json() : item;
      setSelectedItem(fullData);
    } catch (err) {
      console.warn('Không gọi được API chi tiết, dùng dữ liệu danh sách:', err);
    } finally {
      setModalLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    fetchPriceLists();
  }, [fetchPriceLists]);

  const handleFilterChange = (setter, value) => {
    setter(value);
    setPage(1);
  };

  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  // 3. Phê duyệt
  const handleApprove = async (item) => {
    const priceCode = getItemCode(item);

    if (!priceCode) {
      alert('Không tìm thấy Mã định danh bảng giá!');
      console.error('Dữ liệu không có ID/Code:', item);
      return;
    }

    const managerName = user?.fullName || user?.name || 'Manager';

    try {
      const res = await fetch(`${APPROVAL_API}/${priceCode}/manager-approve`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Id': user?.id || '' 
        },
        body: JSON.stringify({ approved_by: managerName, action: 'APPROVE' })
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || `Lỗi (${res.status})`);
      }

      setSelectedItem(null);
      await Promise.all([fetchPriceLists(), fetchStats()]);

      setModalConfig({
        isOpen: true,
        type: 'approve',
        title: 'Đã phê duyệt thành công!',
        message: `Bảng giá mã ${priceCode} đã chuyển sang trạng thái APPROVED.`
      });
    } catch (err) {
      alert(`Phê duyệt thất bại: ${err.message}`);
    }
  };

  // 4. Từ chối
  const handleRejectSubmit = async () => {
    const trimmedReason = rejectModal.reason.trim();
    if (!trimmedReason) {
      alert('Vui lòng nhập lý do từ chối!');
      return;
    }

    const priceCode = getItemCode(rejectModal.item);

    if (!priceCode) {
      alert('Không tìm thấy Mã định danh bảng giá!');
      return;
    }

    const managerName = user?.fullName || user?.name || 'Manager';

    try {
      const res = await fetch(`${APPROVAL_API}/${priceCode}/manager-approve`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Id': user?.id || ''
        },
        body: JSON.stringify({ 
          action: 'REJECT', 
          comment: trimmedReason, 
          approved_by: managerName
        })
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || `Lỗi (${res.status})`);
      }

      setSelectedItem(null);
      setRejectModal({ isOpen: false, item: null, reason: '' });
      await Promise.all([fetchPriceLists(), fetchStats()]);

      setModalConfig({
        isOpen: true,
        type: 'reject',
        title: 'Đã từ chối bảng giá!',
        message: `Bảng giá ${priceCode} đã chuyển sang trạng thái REJECTED.`
      });
    } catch (err) {
      alert(`Từ chối thất bại: ${err.message}`);
    }
  };

  const renderStatusBadge = (status) => {
    const s = (status || 'DRAFT').toUpperCase();
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

  return (
    <div className="space-y-4 font-sans text-slate-700">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Quản lý & Phê duyệt Bảng giá</h1>
          <p className="text-xs text-slate-500 mt-1">Xác nhận phê duyệt bảng giá dịch vụ từ cấp Quản lý qua Manager Approve API.</p>
        </div>
        <button className="px-3.5 py-2 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-2 shadow-xs cursor-pointer">
          <Download className="w-3.5 h-3.5 text-slate-500" />
          <span>Xuất Báo cáo Excel</span>
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500">Tổng số bảng giá</p>
            <p className="text-xl font-bold text-slate-800 mt-0.5">{stats.total}</p>
          </div>
          <div className="p-2 rounded-lg bg-slate-50 text-slate-400">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500">Chờ duyệt (SUBMITTED)</p>
            <p className="text-xl font-bold text-amber-600 mt-0.5">{stats.submitted}</p>
          </div>
          <div className="p-2 rounded-lg bg-amber-50 text-amber-600">
            <Hourglass className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500">Đã duyệt (APPROVED)</p>
            <p className="text-xl font-bold text-blue-600 mt-0.5">{stats.approved || 0}</p>
          </div>
          <div className="p-2 rounded-lg bg-blue-50 text-blue-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500">Hiệu lực (EFFECTIVE)</p>
            <p className="text-xl font-bold text-emerald-600 mt-0.5">{stats.effective}</p>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] font-medium text-slate-500">Bị từ chối (REJECTED)</p>
            <p className="text-xl font-bold text-rose-600 mt-0.5">{stats.rejected}</p>
          </div>
          <div className="p-2 rounded-lg bg-rose-50 text-rose-600">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center space-x-1.5 bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
              <span className="text-slate-500">Loại áp dụng:</span>
              <select 
                value={typeFilter} 
                onChange={(e) => handleFilterChange(setTypeFilter, e.target.value)} 
                className="bg-transparent font-semibold text-slate-800 outline-none cursor-pointer"
              >
                <option value="ALL">Tất cả</option>
                <option value="CUSTOMER">CUSTOMER</option>
                <option value="CONTRACT">CONTRACT</option>
                <option value="GENERAL">GENERAL</option>
                <option value="SERVICE_GROUP">SERVICE_GROUP</option>
                <option value="SERVICE_TYPE">SERVICE_TYPE</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="bg-slate-100/80 p-0.5 rounded-lg flex items-center text-[11px] font-medium text-slate-500">
              {[
                { key: 'ALL', label: 'Tất cả' },
                { key: 'SUBMITTED', label: 'SUBMITTED' },
                { key: 'APPROVED', label: 'APPROVED' },
                { key: 'EFFECTIVE', label: 'EFFECTIVE' },
                { key: 'DRAFT', label: 'DRAFT' },
                { key: 'REJECTED', label: 'REJECTED' }
              ].map((tab) => (
                <button 
                  key={tab.key} 
                  onClick={() => handleFilterChange(setStatusFilter, tab.key)} 
                  className={`px-3 py-1 rounded-md transition cursor-pointer ${statusFilter === tab.key ? 'bg-white text-slate-800 shadow-xs font-semibold' : 'hover:text-slate-800'}`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                value={searchTerm} 
                onChange={(e) => handleFilterChange(setSearchTerm, e.target.value)} 
                placeholder="Tìm kiếm..." 
                className="pl-8 pr-3 py-1 rounded-lg border border-slate-200 text-xs w-48 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400" 
              />
            </div>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/50 text-[11px] font-semibold text-slate-500">
                <th className="py-3 px-4">Mã bảng giá</th>
                <th className="py-3 px-4">Tên bảng giá</th>
                <th className="py-3 px-4">Loại áp dụng</th>
                <th className="py-3 px-4">Phiên bản</th>
                <th className="py-3 px-4">Thời gian hiệu lực</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4">Tạo bởi</th>
                <th className="py-3 px-4 text-center">Thao tác duyệt</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <div className="flex flex-col items-center justify-center space-y-2">
                      <Loader2 className="w-6 h-6 animate-spin text-sky-600" />
                      <span>Đang tải dữ liệu từ server...</span>
                    </div>
                  </td>
                </tr>
              ) : priceLists.length > 0 ? (
                priceLists.map((item, index) => {
                  const code = getItemCode(item) || `PL-${index}`;
                  const name = item.name || item.priceName || item.price_name || 'Bảng giá dịch vụ';
                  const status = (item.status || 'DRAFT').toUpperCase();

                  return (
                    <tr key={code} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-4 font-semibold text-slate-900">{code}</td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-800">{name}</div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">
                          {item.type || item.targetType || 'GENERAL'}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600 font-medium">{item.version || 'v1.0'}</td>
                      <td className="py-3 px-4 text-slate-600">{item.effectiveTime || `${item.effectiveFrom || item.effective_from || ''} - ${item.effectiveTo || item.effective_to || ''}`}</td>
                      <td className="py-3 px-4">{renderStatusBadge(status)}</td>
                      <td className="py-3 px-4">
                        <div className="text-slate-800 font-medium">{item.createdBy || item.created_by || 'Admin'}</div>
                        <div className="text-[10px] text-slate-400">{item.createdAt || item.updatedAt || ''}</div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-1.5">
                          <button onClick={() => handleOpenDetail(item)} className="p-1 text-slate-400 hover:text-sky-600 rounded transition cursor-pointer" title="Xem chi tiết">
                            <Eye className="w-4 h-4" />
                          </button>

                          {status === 'SUBMITTED' && (
                            <>
                              <button onClick={() => handleApprove(item)} className="p-1 text-emerald-600 hover:bg-emerald-50 rounded transition cursor-pointer" title="Duyệt">
                                <Check className="w-4 h-4" />
                              </button>
                              <button onClick={() => setRejectModal({ isOpen: true, item, reason: '' })} className="p-1 text-rose-600 hover:bg-rose-50 rounded transition cursor-pointer" title="Từ chối">
                                <X className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
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

        {/* Pagination */}
        <div className="p-3.5 border-t border-slate-200 bg-white flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div>
            Hiển thị trang hiện tại <strong className="text-slate-800 font-semibold">{priceLists.length}</strong> trong tổng số <strong className="text-slate-800 font-semibold">{totalItems}</strong> bảng giá
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

      {/* Modal Chi tiết Bảng giá */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-[92vw] max-w-[800px] p-6 shadow-2xl space-y-5 max-h-[88vh] flex flex-col border border-slate-100">
            <div className="flex items-start justify-between border-b border-slate-100 pb-3.5">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-mono text-sky-600 font-bold bg-sky-50 px-2 py-0.5 rounded border border-sky-200">
                    {getItemCode(selectedItem)}
                  </span>
                  <span className="text-[11px] font-mono text-slate-600 font-semibold bg-slate-100 px-2 py-0.5 rounded">
                    Phiên bản: {selectedItem.version || '1.0'}
                  </span>
                  {renderStatusBadge(selectedItem.status)}
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  {selectedItem.priceName || selectedItem.name || 'Chi tiết bảng giá'}
                </h3>
              </div>
              <button 
                onClick={() => setSelectedItem(null)} 
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {modalLoading ? (
              <div className="py-12 flex flex-col items-center justify-center space-y-2 text-slate-400">
                <Loader2 className="w-6 h-6 animate-spin text-sky-600" />
                <span className="text-xs">Đang tải toàn bộ thông tin chi tiết...</span>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-5 pr-1">
                <div className="space-y-3">
                  <h4 className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                    <span className="text-[#2b727d]">|</span>
                    <span>1. Thông tin chung bảng giá</span>
                  </h4>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs bg-slate-50/60 p-3.5 rounded-xl border border-slate-100">
                    <div>
                      <span className="block text-slate-400 text-[11px] font-medium mb-0.5">Mã bảng giá</span>
                      <p className="font-semibold text-slate-800 font-mono">{getItemCode(selectedItem) || '-'}</p>
                    </div>

                    <div>
                      <span className="block text-slate-400 text-[11px] font-medium mb-0.5">Tên bảng giá</span>
                      <p className="font-semibold text-slate-800">{selectedItem.priceName || selectedItem.name || '-'}</p>
                    </div>

                    <div>
                      <span className="block text-slate-400 text-[11px] font-medium mb-0.5">Loại đối tượng áp dụng</span>
                      <p className="font-semibold text-slate-800">{selectedItem.targetType || selectedItem.scopeType || selectedItem.type || 'Khách hàng (CUSTOMER)'}</p>
                    </div>

                    <div>
                      <span className="block text-slate-400 text-[11px] font-medium mb-0.5">Đối tượng áp dụng cụ thể</span>
                      <p className="font-semibold text-slate-800">{selectedItem.specificTarget || selectedItem.scopeId || selectedItem.target || 'Tất cả'}</p>
                    </div>

                    <div>
                      <span className="block text-slate-400 text-[11px] font-medium mb-0.5">Thời gian hiệu lực từ</span>
                      <p className="font-semibold text-slate-800 flex items-center space-x-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{selectedItem.effectiveFrom || selectedItem.validFrom || selectedItem.effective_from || '-'}</span>
                      </p>
                    </div>

                    <div>
                      <span className="block text-slate-400 text-[11px] font-medium mb-0.5">Thời gian hiệu lực đến</span>
                      <p className="font-semibold text-slate-800 flex items-center space-x-1">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>{selectedItem.effectiveTo || selectedItem.validTo || selectedItem.effective_to || '-'}</span>
                      </p>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-800 flex items-center space-x-1.5">
                      <span className="text-[#2b727d]">|</span>
                      <span>2. Cấu hình đơn giá dịch vụ chi tiết</span>
                    </h4>
                    <span className="text-[11px] text-slate-500 font-medium">
                      Tổng số: <strong className="text-slate-800">{selectedItem.services?.length || 0}</strong> dịch vụ
                    </span>
                  </div>

                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-slate-50/80 text-slate-600 font-semibold border-b border-slate-200 text-[11px]">
                          <th className="py-2.5 px-3.5">Mã DV</th>
                          <th className="py-2.5 px-3.5">Tên dịch vụ</th>
                          <th className="py-2.5 px-3.5">Đơn vị</th>
                          <th className="py-2.5 px-3.5 text-right">Đơn giá định mức</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 bg-white">
                        {selectedItem.services && selectedItem.services.length > 0 ? (
                          selectedItem.services.map((srv, idx) => (
                            <tr key={srv.id || srv.code || srv.serviceCode || idx} className="hover:bg-slate-50/80 transition">
                              <td className="py-2.5 px-3.5 font-mono text-slate-600 font-semibold">
                                {srv.serviceCode || srv.code}
                              </td>
                              <td className="py-2.5 px-3.5 font-medium text-slate-800">
                                {srv.serviceName || srv.name}
                              </td>
                              <td className="py-2.5 px-3.5 text-slate-500">
                                {srv.unit || '-'}
                              </td>
                              <td className="py-2.5 px-3.5 text-right">
                                <span className="font-bold text-slate-900 mr-1">
                                  {Number(srv.price || srv.unitPrice || 0).toLocaleString('vi-VN')}
                                </span>
                                <span className="text-[10px] text-slate-400 font-medium">VND</span>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={4} className="py-8 text-center text-slate-400 text-xs">
                              Không tìm thấy danh sách dịch vụ chi tiết.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            )}

            <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-100">
              <button 
                onClick={() => setSelectedItem(null)} 
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold transition cursor-pointer"
              >
                Đóng
              </button>

              {selectedItem.status === 'SUBMITTED' && (
                <>
                  <button 
                    onClick={() => setRejectModal({ isOpen: true, item: selectedItem, reason: '' })} 
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                  >
                    Từ chối
                  </button>
                  <button 
                    onClick={() => handleApprove(selectedItem)} 
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                  >
                    Phê duyệt
                  </button>
                </>
              )}
            </div>

          </div>
        </div>
      )}

      {/* Modal Lý do Từ chối */}
      {rejectModal.isOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-5 shadow-2xl space-y-4 border border-slate-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="text-sm font-bold text-rose-600 flex items-center space-x-1.5">
                <AlertCircle className="w-4 h-4" />
                <span>Từ chối phê duyệt</span>
              </h3>
              <button onClick={() => setRejectModal({ isOpen: false, item: null, reason: '' })} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>
            <textarea
              rows={3}
              value={rejectModal.reason}
              onChange={(e) => setRejectModal({ ...rejectModal, reason: e.target.value })}
              placeholder="Nhập lý do từ chối..."
              className="w-full text-xs p-2.5 border border-slate-200 rounded-xl focus:outline-none focus:border-rose-500 bg-slate-50/50"
            />
            <div className="flex justify-end space-x-2 pt-2">
              <button onClick={() => setRejectModal({ isOpen: false, item: null, reason: '' })} className="px-3.5 py-2 bg-slate-100 text-slate-600 rounded-lg text-xs font-semibold">
                Hủy bỏ
              </button>
              <button onClick={handleRejectSubmit} className="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold">
                Xác nhận Từ Chối
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Alert Modal */}
      {modalConfig.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-6 text-center space-y-4">
            <div className="flex justify-center">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${modalConfig.type === 'approve' ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                {modalConfig.type === 'approve' ? <Check className="w-6 h-6 stroke-[3]" /> : <X className="w-6 h-6 stroke-[3]" />}
              </div>
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-900">{modalConfig.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{modalConfig.message}</p>
            </div>
            <button onClick={() => setModalConfig({ ...modalConfig, isOpen: false })} className={`w-full py-2 px-4 rounded-xl text-xs font-bold text-white shadow-md transition cursor-pointer ${modalConfig.type === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'}`}>
              Đóng thông báo
            </button>
          </div>
        </div>
      )}
    </div>
  );
}