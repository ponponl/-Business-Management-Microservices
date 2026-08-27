import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  CheckCircle2, XCircle, Eye, Search, Download, Check, X, AlertCircle, Loader2,
  ChevronLeft, ChevronRight, Calendar, ShieldCheck, Crown, RefreshCw, Copy
} from 'lucide-react';

// API Configuration
const BASE_URL = 'http://localhost:8082/api/v1';
const APPROVAL_API = `${BASE_URL}/approvals`;
const PRICE_LIST_API = `${BASE_URL}/price-lists`;

export default function DirectorPriceListApprovalPage({ user }) {
  // States
  const [stats, setStats] = useState({ approved: 0, effective: 0, rejected: 0, total: 0 });
  const [rawData, setRawData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // Filter states
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Pagination states
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Modals
  const [selectedItem, setSelectedItem] = useState(null);
  const [modalLoading, setModalLoading] = useState(false);
  const [rejectModal, setRejectModal] = useState({ isOpen: false, item: null, reason: '' });

  // Headers auth
  const getAuthHeaders = useCallback(() => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token') || user?.token || ''}`,
    'X-User-Id': user?.id || ''
  }), [user]);

  // --- XỬ LÝ MÃ BẢNG GIÁ ĐẸP (ƯU TIÊN MÃ NGẮN NẾU DÙNG UUID THÌ CẮT GỌN) ---
  const getItemCode = (item) => {
    const rawCode = item?.price_code || item?.price_list_code || item?.priceCode || item?.code;
    if (rawCode && !rawCode.includes('-4') && rawCode.length < 25) {
      return rawCode; // Ví dụ: SCOPE-PL-2026-011
    }
    const fallbackId = item?.price_list_id || item?.id || rawCode || '';
    if (fallbackId.length > 15) {
      return `${fallbackId.substring(0, 8)}...`; // Cắt UUID dài sọc thành 3a87b124...
    }
    return fallbackId || '-';
  };

  const getFullCode = (item) => item?.price_code || item?.price_list_code || item?.price_list_id || item?.id || '';

  // --- LẤY TRẠNG THÁI VÀ LOẠI ÁP DỤNG CHUẨN TỪ BE ---
  const getItemStatus = (item) => String(item?.status || item?.approval_status || '').trim().toUpperCase();

  const getItemType = (item) => {
    const rawType = String(item?.target_type || item?.scope_type || item?.targetType || '').trim().toUpperCase();
    if (rawType.includes('CUSTOMER')) return 'CUSTOMER';
    if (rawType.includes('CONTRACT')) return 'CONTRACT';
    if (rawType.includes('SERVICE')) return 'SERVICE_GROUP';
    return rawType || 'GENERAL';
  };

  // Helper date
  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === '-') return '-';
    try {
      const parts = dateStr.split('/');
      if (parts.length === 3) return dateStr; // Đã đúng định dạng dd/mm/yyyy từ BE
      const date = new Date(dateStr);
      return isNaN(date.getTime()) ? dateStr : date.toLocaleDateString('vi-VN');
    } catch { return dateStr; }
  };

  // Lấy Thống kê cho Giám đốc
  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch(`${APPROVAL_API}/director-approval/stats`, { headers: getAuthHeaders() });
      if (res.ok) {
        const data = await res.json();
        setStats({ 
          approved: data.approved || 0, 
          effective: data.effective || 0, 
          rejected: data.rejected || 0,
          total: data.total || 0
        });
      }
    } catch (err) { console.error('Lỗi lấy thống kê:', err); }
  }, [getAuthHeaders]);

  // Lấy Danh sách theo Trạng thái (Gửi params chuẩn theo BE)
  const fetchPriceLists = useCallback(async () => {
    setLoading(true);
    try {
      const queryParam = statusFilter !== 'ALL' ? `?status=${statusFilter}` : '';
      const res = await fetch(`${APPROVAL_API}/director-list${queryParam}`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error();
      const data = await res.json();
      setRawData(Array.isArray(data) ? data : (data.items || data.data || []));
    } catch { 
      setRawData([]); 
    } finally { 
      setLoading(false); 
    }
  }, [getAuthHeaders, statusFilter]);

  useEffect(() => {
    fetchStats();
    fetchPriceLists();
  }, [fetchStats, fetchPriceLists]);

  // --- BỘ LỌC CLIENT ĐA TẦNG (LỌC LOẠI & TÌM KIẾM TÊN/MÃ) ---
  const filteredLists = useMemo(() => {
    return rawData.filter(item => {
      // 1. Lọc Trạng thái (Nếu BE chưa lọc hết)
      const itemStatus = getItemStatus(item);
      const statusMatch = statusFilter === 'ALL' || itemStatus === statusFilter;

      // 2. Lọc Loại áp dụng
      const itemType = getItemType(item);
      const typeMatch = typeFilter === 'ALL' || itemType === typeFilter;

      // 3. Tìm kiếm tên/mã/đối tượng
      const term = searchTerm.trim().toLowerCase();
      const code = getFullCode(item).toLowerCase();
      const name = String(item?.price_name || item?.name || '').toLowerCase();
      const target = String(item?.specific_target || item?.customer_name || '').toLowerCase();
      const searchMatch = !term || code.includes(term) || name.includes(term) || target.includes(term);

      return statusMatch && typeMatch && searchMatch;
    });
  }, [rawData, statusFilter, typeFilter, searchTerm]);

  // Phân trang Client
  const paginatedLists = useMemo(() => {
    const startIndex = (page - 1) * pageSize;
    return filteredLists.slice(startIndex, startIndex + pageSize);
  }, [filteredLists, page, pageSize]);

  const totalPages = Math.ceil(filteredLists.length / pageSize) || 1;

  // Event Handlers
  const handleStatusFilterChange = (statusKey) => {
    setStatusFilter(statusKey);
    setPage(1);
  };

  const handleTypeFilterChange = (typeKey) => {
    setTypeFilter(typeKey);
    setPage(1);
  };

  const handleOpenDetail = async (item) => {
    const code = getFullCode(item);
    if (!code) return;
    setModalLoading(true);
    setSelectedItem(item);
    try {
      const res = await fetch(`${PRICE_LIST_API}/${code}`, { headers: getAuthHeaders() });
      if (res.ok) {
        const fullData = await res.json();
        setSelectedItem(prev => ({ ...prev, ...fullData }));
      }
    } catch (err) { console.warn(err); } 
    finally { setModalLoading(false); }
  };

  // Giám đốc duyệt
  const handleDirectorApprove = async (item) => {
    const priceCode = getFullCode(item);
    if (!priceCode) return alert('Không tìm thấy mã bảng giá!');
    setActionLoadingId(priceCode);
    try {
      const res = await fetch(`${APPROVAL_API}/${priceCode}/director-approve`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ action: 'APPROVE', comment: 'Đã duyệt bởi Giám Đốc' })
      });
      if (!res.ok) throw new Error();
      setSelectedItem(null);
      await Promise.all([fetchPriceLists(), fetchStats()]);
    } catch (err) { alert('Phê duyệt thất bại!'); } 
    finally { setActionLoadingId(null); }
  };

  // Giám đốc từ chối
  const handleDirectorRejectSubmit = async () => {
    if (!rejectModal.reason.trim()) return alert('Vui lòng nhập lý do từ chối!');
    const priceCode = getFullCode(rejectModal.item);
    setActionLoadingId(priceCode);
    try {
      const res = await fetch(`${APPROVAL_API}/${priceCode}/director-approve`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ 
          action: 'REJECT', 
          rejected_reason: rejectModal.reason,
          comment: rejectModal.reason
        })
      });
      if (!res.ok) throw new Error();
      setSelectedItem(null);
      setRejectModal({ isOpen: false, item: null, reason: '' });
      await Promise.all([fetchPriceLists(), fetchStats()]);
    } catch (err) { alert('Từ chối thất bại!'); } 
    finally { setActionLoadingId(null); }
  };

  const renderStatusBadge = (status) => {
    const s = String(status || '').toUpperCase();
    const style = s === 'APPROVED' ? 'bg-blue-100 text-blue-700 font-bold border border-blue-200' 
                : s === 'EFFECTIVE' ? 'bg-emerald-100 text-emerald-700 font-bold border border-emerald-200' 
                : s === 'REJECTED' ? 'bg-rose-100 text-rose-700 font-bold border border-rose-200' 
                : 'bg-slate-100 text-slate-600';
    return <span className={`px-2 py-0.5 rounded text-[10px] tracking-wide ${style}`}>{s}</span>;
  };

  return (
    <div className="space-y-3 font-sans text-slate-700 text-xs">
      {/* Header */}
      <div className="flex items-center justify-between gap-2 border-b border-slate-200 pb-2">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-amber-100 text-amber-700 rounded-lg"><Crown className="w-4 h-4" /></div>
          <div>
            <h1 className="text-base font-bold text-slate-800">Phê duyệt Bảng giá - Ban Giám Đốc</h1>
            <span className="text-[11px] text-slate-400">Cấp phê duyệt cuối (APPROVED &rarr; EFFECTIVE)</span>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button onClick={() => { fetchPriceLists(); fetchStats(); }} className="p-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 rounded-lg text-xs font-semibold flex items-center shadow-xs cursor-pointer">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button className="px-2.5 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-1.5 shadow-xs cursor-pointer">
            <Download className="w-3.5 h-3.5 text-slate-500" /><span>Xuất Báo Cáo</span>
          </button>
        </div>
      </div>

      {/* Thống kê Thẻ */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <div onClick={() => handleStatusFilterChange('APPROVED')} className={`bg-white p-2.5 rounded-lg border flex items-center justify-between cursor-pointer transition ${statusFilter === 'APPROVED' ? 'ring-2 ring-blue-500 border-transparent' : 'border-slate-200 hover:border-blue-300'}`}>
          <div><p className="text-[10px] font-medium text-slate-500">Chờ Duyệt (APPROVED)</p><p className="text-base font-bold text-blue-600 leading-tight">{stats.approved}</p></div>
          <ShieldCheck className="w-5 h-5 text-blue-500" />
        </div>
        <div onClick={() => handleStatusFilterChange('EFFECTIVE')} className={`bg-white p-2.5 rounded-lg border flex items-center justify-between cursor-pointer transition ${statusFilter === 'EFFECTIVE' ? 'ring-2 ring-emerald-500 border-transparent' : 'border-slate-200 hover:border-emerald-300'}`}>
          <div><p className="text-[10px] font-medium text-slate-500">Hiệu lực (EFFECTIVE)</p><p className="text-base font-bold text-emerald-600 leading-tight">{stats.effective}</p></div>
          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
        </div>
        <div onClick={() => handleStatusFilterChange('REJECTED')} className={`bg-white p-2.5 rounded-lg border flex items-center justify-between cursor-pointer transition ${statusFilter === 'REJECTED' ? 'ring-2 ring-rose-500 border-transparent' : 'border-slate-200 hover:border-rose-300'}`}>
          <div><p className="text-[10px] font-medium text-slate-500">Đã từ chối (REJECTED)</p><p className="text-base font-bold text-rose-600 leading-tight">{stats.rejected}</p></div>
          <XCircle className="w-5 h-5 text-rose-500" />
        </div>
      </div>

      {/* Thanh lọc chuẩn hoá */}
      <div className="bg-white p-2 rounded-lg border border-slate-200 flex flex-wrap items-center justify-between gap-2 shadow-2xs">
        {/* Lọc theo Loại Áp Dụng */}
        <div className="flex items-center space-x-1.5 bg-slate-50 px-2 py-1 rounded border border-slate-200 text-xs">
          <span className="text-slate-400 text-[11px] font-medium">Loại:</span>
          <select value={typeFilter} onChange={(e) => handleTypeFilterChange(e.target.value)} className="bg-transparent font-semibold text-slate-700 outline-none cursor-pointer text-xs">
            <option value="ALL">ALL (Tất cả)</option>
            <option value="CUSTOMER">CUSTOMER</option>
            <option value="CONTRACT">CONTRACT</option>
            <option value="GENERAL">GENERAL</option>
            <option value="SERVICE_GROUP">SERVICE_GROUP</option>
          </select>
        </div>

        {/* Lọc theo Trạng Thái (Tab) */}
        <div className="bg-slate-100 p-0.5 rounded-md flex items-center space-x-0.5 text-[11px] font-medium text-slate-500">
          {[
            { key: 'ALL', label: 'TẤT CẢ' },
            { key: 'APPROVED', label: 'APPROVED' },
            { key: 'EFFECTIVE', label: 'EFFECTIVE' },
            { key: 'REJECTED', label: 'REJECTED' }
          ].map((tab) => (
            <button key={tab.key} type="button" onClick={() => handleStatusFilterChange(tab.key)} className={`px-3 py-1 rounded transition cursor-pointer ${statusFilter === tab.key ? 'bg-white text-slate-900 shadow-xs font-bold' : 'hover:text-slate-800'}`}>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Ô Tìm kiếm */}
        <div className="relative flex-1 sm:flex-initial min-w-[160px]">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="Tìm mã, tên bảng giá..." className="w-full pl-7 pr-2 py-1 rounded border border-slate-200 text-xs focus:outline-none focus:border-amber-500 bg-white placeholder:text-slate-400" />
        </div>
      </div>

      {/* Bảng Dữ Liệu */}
      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-2xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse whitespace-nowrap">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-[11px] font-semibold text-slate-500">
                <th className="py-2.5 px-3">Mã bảng giá</th>
                <th className="py-2.5 px-3">Tên bảng giá / Đối tượng</th>
                <th className="py-2.5 px-3">Loại áp dụng</th>
                <th className="py-2.5 px-3">Phiên bản</th>
                <th className="py-2.5 px-3">Thời gian hiệu lực</th>
                <th className="py-2.5 px-3">Trạng thái</th>
                <th className="py-2.5 px-3">Người cập nhật</th>
                <th className="py-2.5 px-3 text-center">Hành động</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs text-slate-700">
              {loading ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td colSpan={8} className="py-3 px-3"><div className="h-4 bg-slate-100 rounded w-full"></div></td>
                  </tr>
                ))
              ) : paginatedLists.length > 0 ? (
                paginatedLists.map((item, index) => {
                  const displayCode = getItemCode(item);
                  const fullCode = getFullCode(item);
                  const name = item.price_name || item.name || 'Bảng giá dịch vụ';
                  const subTarget = item.specific_target || item.customer_name || 'N/A';
                  const targetType = getItemType(item);
                  const effectiveFrom = formatDate(item.effective_from);
                  const effectiveTo = formatDate(item.effective_to);
                  const updatedBy = item.updated_by || 'Manager';
                  const updatedAt = item.updated_at || '-';
                  const status = getItemStatus(item);
                  const isActioning = actionLoadingId === fullCode;

                  return (
                    <tr key={fullCode || index} className="hover:bg-slate-50/80 transition border-b border-slate-100">
                      {/* Mã ngắn gọn */}
                      <td className="py-2.5 px-3 font-mono font-bold text-slate-800">
                        <span className="bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200" title={fullCode}>
                          {displayCode}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 max-w-[220px]">
                        <div className="font-bold text-slate-800 leading-snug truncate">{name}</div>
                        <div className="text-[10px] font-mono text-slate-400 truncate leading-none mt-0.5">{subTarget}</div>
                      </td>
                      <td className="py-2.5 px-3">
                        <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">{targetType}</span>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500 font-bold">{item.version || 'v1.0'}</td>
                      <td className="py-2.5 px-3 text-slate-600 font-medium">{`${effectiveFrom} - ${effectiveTo}`}</td>
                      <td className="py-2.5 px-3">{renderStatusBadge(status)}</td>
                      <td className="py-2.5 px-3">
                        <div className="font-semibold text-slate-800 leading-snug">{updatedBy}</div>
                        <div className="text-[10px] text-slate-400 font-mono leading-none mt-0.5">{updatedAt}</div>
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {isActioning ? (
                          <Loader2 className="w-4 h-4 animate-spin text-amber-600 mx-auto" />
                        ) : (
                          <div className="flex items-center justify-center space-x-1">
                            <button onClick={() => handleOpenDetail(item)} className="p-1 text-slate-400 hover:text-amber-600 rounded cursor-pointer" title="Xem chi tiết">
                              <Eye className="w-4 h-4" />
                            </button>
                            {status === 'APPROVED' && (
                              <>
                                <button onClick={() => handleDirectorApprove(item)} className="p-1 text-emerald-600 hover:bg-emerald-50 rounded cursor-pointer" title="Duyệt Hiệu Lực (EFFECTIVE)">
                                  <Check className="w-4 h-4 stroke-[3]" />
                                </button>
                                <button onClick={() => setRejectModal({ isOpen: true, item, reason: '' })} className="p-1 text-rose-600 hover:bg-rose-50 rounded cursor-pointer" title="Từ chối">
                                  <X className="w-4 h-4 stroke-[3]" />
                                </button>
                              </>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400 text-xs">
                    <div className="flex flex-col items-center justify-center space-y-1">
                      <AlertCircle className="w-5 h-5 text-slate-300" />
                      <span>Không tìm thấy dữ liệu phù hợp với bộ lọc.</span>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Phân trang */}
        <div className="px-3 py-2 border-t border-slate-100 bg-white flex items-center justify-between text-xs text-slate-500">
          <div>Hiển thị <strong className="text-slate-800">{paginatedLists.length}</strong> / <strong className="text-slate-800">{filteredLists.length}</strong> bản ghi</div>
          <div className="flex items-center space-x-1">
            <button disabled={page <= 1} onClick={() => setPage(prev => Math.max(prev - 1, 1))} className="p-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"><ChevronLeft className="w-3.5 h-3.5" /></button>
            <span className="px-2 py-0.5 rounded bg-slate-800 text-white font-medium text-[11px]">{page} / {totalPages}</span>
            <button disabled={page >= totalPages} onClick={() => setPage(prev => Math.min(prev + 1, totalPages))} className="p-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40 cursor-pointer"><ChevronRight className="w-3.5 h-3.5" /></button>
          </div>
        </div>
      </div>

      {/* Modal chi tiết */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-2xl p-4 shadow-2xl space-y-3 max-h-[85vh] flex flex-col border border-slate-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <div className="flex items-center space-x-2">
                <span className="text-[11px] font-mono text-amber-600 font-bold bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">{getItemCode(selectedItem)}</span>
                <h3 className="text-sm font-bold text-slate-900 truncate max-w-[300px]">{selectedItem.price_name || selectedItem.name}</h3>
                {renderStatusBadge(getItemStatus(selectedItem))}
              </div>
              <button onClick={() => setSelectedItem(null)} className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"><X className="w-4 h-4" /></button>
            </div>

            {modalLoading ? (
              <div className="py-8 flex flex-col items-center justify-center space-y-2 text-slate-400"><Loader2 className="w-5 h-5 animate-spin text-amber-600" /><span className="text-xs">Đang tải chi tiết...</span></div>
            ) : (
              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div><span className="block text-slate-400 text-[10px]">Loại đối tượng</span><p className="font-semibold text-slate-800">{getItemType(selectedItem)}</p></div>
                  <div><span className="block text-slate-400 text-[10px]">Đối tượng áp dụng</span><p className="font-semibold text-slate-800 truncate">{selectedItem.specific_target || 'Tất cả'}</p></div>
                  <div><span className="block text-slate-400 text-[10px]">Phiên bản</span><p className="font-semibold text-slate-800 font-mono">{selectedItem.version || 'v1.0'}</p></div>
                  <div className="col-span-2 sm:col-span-3 flex items-center space-x-3 text-[11px] text-slate-600 pt-1 border-t border-slate-200/60">
                    <span className="flex items-center space-x-1"><Calendar className="w-3 h-3 text-slate-400" /><span>Hiệu lực từ: {formatDate(selectedItem.effective_from)}</span></span>
                    <span className="flex items-center space-x-1"><Calendar className="w-3 h-3 text-slate-400" /><span>Đến: {formatDate(selectedItem.effective_to)}</span></span>
                  </div>
                </div>

                {/* Danh sách Dịch vụ trả về từ BE */}
                {(() => {
                  const serviceList = selectedItem.services || [];
                  return (
                    <div className="space-y-1.5">
                      <div className="text-xs font-bold text-slate-800">Cấu hình đơn giá ({serviceList.length} dịch vụ)</div>
                      <div className="border border-slate-200 rounded-lg overflow-hidden">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="bg-slate-50 text-slate-500 font-semibold border-b border-slate-200 text-[10px]">
                              <th className="py-1.5 px-2.5">Mã DV</th><th className="py-1.5 px-2.5">Tên dịch vụ</th><th className="py-1.5 px-2.5">Đơn vị</th><th className="py-1.5 px-2.5 text-right">Đơn giá</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 bg-white">
                            {serviceList.length > 0 ? (
                              serviceList.map((srv, idx) => (
                                <tr key={srv.service_code || idx} className="hover:bg-slate-50/80">
                                  <td className="py-1.5 px-2.5 font-mono text-slate-500">{srv.service_code || '-'}</td>
                                  <td className="py-1.5 px-2.5 font-medium text-slate-800">{srv.service_name || '-'}</td>
                                  <td className="py-1.5 px-2.5 text-slate-500">{srv.unit || '-'}</td>
                                  <td className="py-1.5 px-2.5 text-right font-bold text-slate-900">{Number(srv.unit_price || 0).toLocaleString('vi-VN')} <span className="text-[10px] text-slate-400 font-normal">VND</span></td>
                                </tr>
                              ))
                            ) : (
                              <tr><td colSpan={4} className="py-4 text-center text-slate-400 text-xs">Không tìm thấy chi tiết đơn giá.</td></tr>
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
              <button onClick={() => setSelectedItem(null)} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold cursor-pointer">Đóng</button>
              {getItemStatus(selectedItem) === 'APPROVED' && (
                <>
                  <button onClick={() => setRejectModal({ isOpen: true, item: selectedItem, reason: '' })} className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold cursor-pointer">Từ chối</button>
                  <button onClick={() => handleDirectorApprove(selectedItem)} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold cursor-pointer">Phê duyệt ngay</button>
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
              <h3 className="text-xs font-bold text-rose-600 flex items-center space-x-1"><AlertCircle className="w-3.5 h-3.5" /><span>Nhập lý do từ chối</span></h3>
              <button onClick={() => setRejectModal({ isOpen: false, item: null, reason: '' })} className="text-slate-400 hover:text-slate-600 cursor-pointer"><X className="w-3.5 h-3.5" /></button>
            </div>
            <textarea rows={3} value={rejectModal.reason} onChange={(e) => setRejectModal({ ...rejectModal, reason: e.target.value })} placeholder="Lý do gửi lại cấp quản lý..." className="w-full text-xs p-2 border border-slate-200 rounded-lg focus:outline-none focus:border-rose-500 bg-slate-50/50" autoFocus />
            <div className="flex justify-end space-x-2 pt-1">
              <button onClick={() => setRejectModal({ isOpen: false, item: null, reason: '' })} className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold cursor-pointer">Hủy</button>
              <button onClick={handleDirectorRejectSubmit} className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold cursor-pointer">Xác nhận từ chối</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}