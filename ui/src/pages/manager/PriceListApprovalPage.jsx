import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Layers, Hourglass, CheckCircle2, XCircle, Eye, Search, 
  Download, Check, X, AlertCircle, Loader2,
  ChevronLeft, ChevronRight, Calendar, ShieldCheck, ShieldAlert
} from 'lucide-react';

const PRICE_LIST_API = 'http://localhost:8082/api/v1/price-lists';
const APPROVAL_API = 'http://localhost:8082/api/v1/approvals';

export default function PriceListApprovalPage({ user }) {
  const token = localStorage.getItem('token');

  const isManager = useMemo(() => {
    if (!user) return false;
    const userRole = (user.role || '').toUpperCase();
    const userRoles = Array.isArray(user.roles) 
      ? user.roles.map(r => String(r).toUpperCase()) 
      : [];
    
    const managerRoles = ['MANAGER', 'ADMIN', 'DIRECTOR', 'APPROVER', 'QUAN_LY'];
    return managerRoles.includes(userRole) || userRoles.some(r => managerRoles.includes(r));
  }, [user]);

  // State Thống kê
  const [stats, setStats] = useState({ total: 0, submitted: 0, approved: 0, effective: 0, rejected: 0 });

  // State Danh sách & Phân trang
  const [priceLists, setPriceLists] = useState([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // State Bộ lọc & Tìm kiếm
  const [activeStatusTab, setActiveStatusTab] = useState('Tất cả');
  const [selectedType, setSelectedType] = useState('Tất cả');
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const availableTypes = ['Tất cả', 'CUSTOMER', 'CONTRACT', 'GENERAL', 'SERVICE_GROUP', 'SERVICE_TYPE'];

  // State Modals
  const [selectedItem, setSelectedItem] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [rejectModal, setRejectModal] = useState({ isOpen: false, item: null, reason: '' });
  const [modalConfig, setModalConfig] = useState({
    isOpen: false,
    type: '',
    title: '',
    message: ''
  });

  // Debounce tìm kiếm
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const getItemCode = (item) => {
    return item?.price_list_id || item?.price_code || item?.price_list_code || item?.id || '';
  };

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === '-') return '-';
    try {
      return dateStr.split('T')[0];
    } catch {
      return dateStr;
    }
  };

  // 1. Lấy số liệu Thống kê
  const fetchStats = useCallback(async () => {
    if (!token) return;
    try {
      const res = await fetch(`${APPROVAL_API}/approval/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!res.ok) throw new Error('Không thể tải thống kê');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      console.error('Lỗi lấy thống kê:', err);
    }
  }, [token]);

  // 2. Lấy danh sách phê duyệt Bảng giá
  const fetchPriceLists = useCallback(async () => {
    if (!token) return;
    setLoading(true);

    const params = new URLSearchParams();
    if (activeStatusTab !== 'Tất cả') {
      params.append('status', activeStatusTab);
    }

    try {
      const res = await fetch(`${APPROVAL_API}?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!res.ok) throw new Error(`Lỗi kết nối API (${res.status})`);
      
      const data = await res.json();
      let rawList = Array.isArray(data) ? data : (data.items || data.data || []);

      // Lọc Client theo Loại áp dụng
      if (selectedType !== 'Tất cả') {
        rawList = rawList.filter(item => item.target_type?.toUpperCase() === selectedType.toUpperCase());
      }

      // Lọc Client theo Tìm kiếm
      if (debouncedSearch.trim() !== '') {
        const term = debouncedSearch.trim().toLowerCase();
        rawList = rawList.filter(item => 
          (item.price_list_id && item.price_list_id.toLowerCase().includes(term)) ||
          (item.price_name && item.price_name.toLowerCase().includes(term)) ||
          (item.specific_target && item.specific_target.toLowerCase().includes(term))
        );
      }

      setTotalItems(rawList.length);

      // Phân trang phía Client
      const startIndex = (page - 1) * pageSize;
      setPriceLists(rawList.slice(startIndex, startIndex + pageSize));
    } catch (err) {
      console.error('Lỗi tải danh sách phê duyệt:', err);
      setPriceLists([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, activeStatusTab, selectedType, debouncedSearch, token]);

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

  const handleOpenDetail = async (item) => {
    const code = getItemCode(item);
    if (!code) return;

    setModalLoading(true);
    setSelectedItem(item);

    try {
      const res = await fetch(`${PRICE_LIST_API}/${code}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (res.ok) {
        const fullData = await res.json();
        setSelectedItem(prev => ({ ...prev, ...fullData }));
      }
    } catch (err) {
      console.warn('Sử dụng dữ liệu danh sách hiện tại:', err);
    } finally {
      setModalLoading(false);
    }
  };

  // 3. Phê duyệt Bảng giá (API Call)
  const handleApprove = async (item) => {
    if (!isManager) {
      alert('Tài khoản của bạn không có quyền phê duyệt bảng giá này!');
      return;
    }

    const priceCode = getItemCode(item);
    if (!priceCode) return;

    const managerName = user?.fullName || user?.username || 'Manager';

    try {
      const res = await fetch(`${APPROVAL_API}/${priceCode}/manager-approve`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-User-Id': user?.id || '' 
        },
        body: JSON.stringify({ 
          action: 'APPROVE',
          approved_by: managerName 
        })
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
        message: `Bảng giá ${priceCode} đã chuyển sang trạng thái APPROVED.`
      });
    } catch (err) {
      alert(`Phê duyệt thất bại: ${err.message}`);
    }
  };

  // 4. Từ chối Bảng giá (API Call)
  const handleRejectSubmit = async () => {
    if (!isManager) {
      alert('Tài khoản của bạn không có quyền từ chối bảng giá này!');
      return;
    }

    const trimmedReason = rejectModal.reason.trim();
    if (!trimmedReason) {
      alert('Vui lòng nhập lý do từ chối!');
      return;
    }

    const priceCode = getItemCode(rejectModal.item);
    if (!priceCode) return;

    const managerName = user?.fullName || user?.username || 'Manager';

    try {
      const res = await fetch(`${APPROVAL_API}/${priceCode}/manager-approve`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'X-User-Id': user?.id || ''
        },
        body: JSON.stringify({ 
          action: 'REJECT', 
          comment: trimmedReason,
          rejected_reason: trimmedReason,
          rejected_by: managerName
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
      case 'SUPERSEDED':
        return <span className="px-2.5 py-0.5 rounded bg-purple-100/70 text-purple-700 text-[10px] font-bold tracking-wide">SUPERSEDED</span>;
      case 'EXPIRED':
        return <span className="px-2.5 py-0.5 rounded bg-gray-200 text-gray-700 text-[10px] font-bold tracking-wide">EXPIRED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-bold">{s}</span>;
    }
  };

  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  return (
    <div className="space-y-4 text-slate-700 font-sans p-4">
      
      {/* Thẻ Cảnh báo nếu User chỉ có quyền Staff */}
      {!isManager && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 px-3.5 py-2.5 rounded-xl flex items-center justify-between shadow-xs">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span className="text-xs font-medium">
              Bạn đang xem ở <strong>Chế độ chỉ đọc (Read-only)</strong>. Tài khoản của bạn không có quyền phê duyệt hoặc từ chối bảng giá.
            </span>
          </div>
        </div>
      )}

      {/* 1. HEADER TRANG & BUTTONS */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800">Quản lý & Phê duyệt Bảng giá</h1>
          <p className="text-xs text-slate-500 mt-1">
            Theo dõi danh sách yêu cầu phê duyệt bảng giá dịch vụ logistics và xét duyệt cấp Quản lý.
          </p>
        </div>
        <div className="flex items-center space-x-2.5">
          <button className="px-3.5 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 shadow-xs flex items-center space-x-1.5 cursor-pointer">
            <Download className="w-3.5 h-3.5 text-slate-500" />
            <span>Xuất Excel</span>
          </button>
        </div>
      </div>

      {/* 2. THỐNG KÊ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Tổng số bảng giá</p>
            <p className="text-xl font-bold text-slate-800 mt-0.5">{stats.total || 0}</p>
          </div>
          <div className="p-2 rounded-lg bg-slate-50 text-slate-400">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Chờ duyệt (SUBMITTED)</p>
            <p className="text-xl font-bold text-amber-600 mt-0.5">{stats.submitted || 0}</p>
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
            <p className="text-xl font-bold text-emerald-600 mt-0.5">{stats.effective || 0}</p>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-[11px] text-slate-500 font-medium">Bị từ chối (REJECTED)</p>
            <p className="text-xl font-bold text-rose-600 mt-0.5">{stats.rejected || 0}</p>
          </div>
          <div className="p-2 rounded-lg bg-rose-50 text-rose-600">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 3. BỘ LỌC */}
      <div className="bg-white p-2.5 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          
          <div className="flex items-center space-x-2">
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
          </div>

          <div className="flex items-center space-x-2 overflow-x-auto max-w-full">
            <div className="bg-slate-100/80 p-0.5 rounded-lg flex items-center text-[11px] font-medium text-slate-500 overflow-x-auto shrink-0">
              {['Tất cả', 'SUBMITTED', 'APPROVED', 'EFFECTIVE', 'DRAFT', 'REJECTED', 'SUPERSEDED', 'EXPIRED'].map((tab) => (
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

            <div className="relative shrink-0">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Tìm kiếm..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="pl-7 pr-2.5 py-1 rounded-lg border border-slate-200 text-[11px] w-36 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
              />
            </div>
          </div>

        </div>
      </div>

      {/* 4. BẢNG DỮ LIỆU */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse whitespace-nowrap">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/50 text-[11px] font-semibold text-slate-500">
                <th className="py-3 px-4">Mã bảng giá</th>
                <th className="py-3 px-4">Tên bảng giá / Đối tượng</th>
                <th className="py-3 px-4">Loại áp dụng</th>
                <th className="py-3 px-4">Phiên bản</th>
                <th className="py-3 px-4">Thời gian hiệu lực</th>
                <th className="py-3 px-4">Trạng thái</th>
                <th className="py-3 px-4">Tạo / Cập nhật</th>
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
                priceLists.map((item) => {
                  const code = getItemCode(item);
                  const name = item.price_name || 'Bảng giá dịch vụ';
                  const subTarget = item.specific_target || 'N/A';
                  const targetType = item.target_type || 'GENERAL';
                  
                  const effectiveFrom = formatDate(item.effective_from);
                  const effectiveTo = formatDate(item.effective_to);
                  
                  const updatedBy = item.updated_by || 'Staff';
                  const updatedAt = item.updated_at || '-';
                  const status = (item.status || 'DRAFT').toUpperCase();
                  const versionStr = item.version || 'v1.0';

                  return (
                    <tr key={code} className="hover:bg-slate-50/70 transition">
                      <td className="py-3 px-4 font-mono font-bold text-slate-900">{code}</td>
                      <td className="py-3 px-4 max-w-[220px]">
                        <div className="font-bold text-slate-800 leading-snug truncate">{name}</div>
                        <div className="text-[10px] font-mono text-slate-400 truncate leading-none mt-0.5">
                          {subTarget}
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">
                          {targetType}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600 font-medium">{versionStr}</td>
                      <td className="py-3 px-4 text-slate-600">{`${effectiveFrom} - ${effectiveTo}`}</td>
                      <td className="py-3 px-4">{renderStatusBadge(status)}</td>
                      <td className="py-3 px-4">
                        <div className="text-slate-800 font-medium leading-snug">{updatedBy}</div>
                        <div className="text-[10px] text-slate-400 font-mono leading-none mt-0.5">{updatedAt}</div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <div className="flex items-center justify-center space-x-1">
                          <button 
                            onClick={() => handleOpenDetail(item)} 
                            className="p-1 text-slate-400 hover:text-sky-600 rounded transition cursor-pointer" 
                            title="Xem chi tiết"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {status === 'SUBMITTED' && isManager && (
                            <>
                              <button 
                                onClick={() => handleApprove(item)} 
                                className="p-1 text-emerald-600 hover:bg-emerald-50 rounded transition cursor-pointer" 
                                title="Phê duyệt"
                              >
                                <Check className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => setRejectModal({ isOpen: true, item, reason: '' })} 
                                className="p-1 text-rose-600 hover:bg-rose-50 rounded transition cursor-pointer" 
                                title="Từ chối"
                              >
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

      {/* Modal Xem chi tiết */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-2xl p-4 shadow-2xl space-y-3 max-h-[85vh] flex flex-col border border-slate-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono text-sky-600 font-bold bg-sky-50 px-1.5 py-0.5 rounded border border-sky-200">
                  {getItemCode(selectedItem)}
                </span>
                <h3 className="text-sm font-bold text-slate-900 truncate max-w-[300px]">
                  {selectedItem.price_name || 'Chi tiết bảng giá'}
                </h3>
                {renderStatusBadge(selectedItem.status)}
              </div>
              <button onClick={() => setSelectedItem(null)} className="text-slate-400 hover:text-slate-600 p-1 rounded transition cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            {modalLoading ? (
              <div className="py-8 flex flex-col items-center justify-center space-y-2 text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin text-[#2b727d]" />
                <span className="text-xs">Đang tải thông tin chi tiết...</span>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div>
                    <span className="block text-slate-400 text-[10px]">Loại đối tượng</span>
                    <p className="font-semibold text-slate-800">{selectedItem.target_type || 'GENERAL'}</p>
                  </div>
                  <div>
                    <span className="block text-slate-400 text-[10px]">Đối tượng cụ thể</span>
                    <p className="font-semibold text-slate-800 truncate">{selectedItem.specific_target || 'Tất cả'}</p>
                  </div>
                  <div>
                    <span className="block text-slate-400 text-[10px]">Phiên bản</span>
                    <p className="font-semibold text-slate-800 font-mono">{selectedItem.version || 'v1.0'}</p>
                  </div>
                  <div className="col-span-2 sm:col-span-3 flex items-center space-x-3 text-[11px] text-slate-600 pt-1 border-t border-slate-200/60">
                    <span className="flex items-center space-x-1">
                      <Calendar className="w-3 h-3 text-slate-400" />
                      <span>Từ: {formatDate(selectedItem.effective_from)}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Calendar className="w-3 h-3 text-slate-400" />
                      <span>Đến: {formatDate(selectedItem.effective_to)}</span>
                    </span>
                  </div>
                </div>

                {(() => {
                  const serviceList = selectedItem.services || selectedItem.items || selectedItem.details || selectedItem.price_list_items || [];
                  return (
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs font-bold text-slate-800">
                        <span>Cấu hình đơn giá ({serviceList.length})</span>
                      </div>

                      <div className="border border-slate-200 rounded-lg overflow-hidden">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px]">
                              <th className="py-1.5 px-2.5">Mã DV</th>
                              <th className="py-1.5 px-2.5">Tên dịch vụ</th>
                              <th className="py-1.5 px-2.5">Đơn vị</th>
                              <th className="py-1.5 px-2.5 text-right">Đơn giá</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {serviceList.length > 0 ? (
                              serviceList.map((srv, idx) => {
                                const serviceCode = srv.service_code || srv.code || srv.service_id || srv.item_code || '-';
                                const serviceName = srv.service_name || srv.name || srv.description || srv.service_type_name || srv.title || '-';
                                const unit = srv.unit || srv.uom || srv.unit_name || '-';
                                const price = srv.price ?? srv.unit_price ?? srv.amount ?? srv.rate ?? 0;

                                return (
                                  <tr key={srv.id || serviceCode || idx} className="hover:bg-slate-50/80">
                                    <td className="py-1.5 px-2.5 font-mono text-slate-500">{serviceCode}</td>
                                    <td className="py-1.5 px-2.5 font-medium text-slate-800">{serviceName}</td>
                                    <td className="py-1.5 px-2.5 text-slate-500">{unit}</td>
                                    <td className="py-1.5 px-2.5 text-right font-bold text-slate-900">
                                      {Number(price).toLocaleString('vi-VN')}{' '}
                                      <span className="text-[10px] text-slate-400 font-normal">VND</span>
                                    </td>
                                  </tr>
                                );
                              })
                            ) : (
                              <tr>
                                <td colSpan={4} className="py-4 text-center text-slate-400 text-xs">
                                  Không có dữ liệu dịch vụ.
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-100">
              <button 
                onClick={() => setSelectedItem(null)} 
                className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold cursor-pointer"
              >
                Đóng
              </button>

              {selectedItem?.status === 'SUBMITTED' && isManager && (
                <>
                  <button 
                    onClick={() => setRejectModal({ isOpen: true, item: selectedItem, reason: '' })} 
                    className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Từ chối
                  </button>
                  <button 
                    onClick={() => handleApprove(selectedItem)} 
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold cursor-pointer"
                  >
                    Phê duyệt
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal Từ chối */}
      {rejectModal.isOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-sm p-4 shadow-2xl space-y-3 border border-slate-100">
            <div className="flex justify-between items-center border-b border-slate-100 pb-2">
              <h3 className="text-xs font-bold text-rose-600 flex items-center space-x-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>Từ chối phê duyệt</span>
              </h3>
              <button onClick={() => setRejectModal({ isOpen: false, item: null, reason: '' })} className="text-slate-400 hover:text-slate-600">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <textarea
              rows={3}
              value={rejectModal.reason}
              onChange={(e) => setRejectModal({ ...rejectModal, reason: e.target.value })}
              placeholder="Nhập lý do từ chối..."
              className="w-full text-xs p-2 border border-slate-200 rounded-lg focus:outline-none focus:border-rose-500 bg-slate-50/50"
            />
            <div className="flex justify-end space-x-2">
              <button onClick={() => setRejectModal({ isOpen: false, item: null, reason: '' })} className="px-3 py-1 bg-slate-100 text-slate-600 rounded-md text-xs font-semibold cursor-pointer">
                Hủy
              </button>
              <button onClick={handleRejectSubmit} className="px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-md text-xs font-semibold cursor-pointer">
                Xác nhận
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Thông báo kết quả */}
      {modalConfig.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-xl border border-slate-100 max-w-xs w-full p-4 text-center space-y-3">
            <div className="flex justify-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${modalConfig.type === 'approve' ? 'bg-emerald-100 text-emerald-600' : 'bg-rose-100 text-rose-600'}`}>
                {modalConfig.type === 'approve' ? <Check className="w-5 h-5 stroke-[3]" /> : <X className="w-5 h-5 stroke-[3]" />}
              </div>
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">{modalConfig.title}</h3>
              <p className="text-[11px] text-slate-500 mt-0.5">{modalConfig.message}</p>
            </div>
            <button onClick={() => setModalConfig({ ...modalConfig, isOpen: false })} className={`w-full py-1.5 px-3 rounded-lg text-xs font-bold text-white shadow-xs cursor-pointer ${modalConfig.type === 'approve' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-rose-600 hover:bg-rose-700'}`}>
              Đóng
            </button>
          </div>
        </div>
      )}

    </div>
  );
}