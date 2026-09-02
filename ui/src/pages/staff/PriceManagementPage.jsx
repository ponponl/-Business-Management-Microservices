import React, { useState, useEffect, useRef } from 'react';
import { 
  Download, Plus, Eye, ChevronLeft, ChevronRight, 
  Search, Layers, Hourglass, CheckCircle2, XCircle, Loader2, ShieldCheck 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API_BASE_URL = 'http://localhost:8082/api/v1/price-lists';
const CONTRACT_SERVICE_URL = 'http://localhost:8083';

export default function PriceManagementPage() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const [stats, setStats] = useState({ total: 0, submitted: 0, approved: 0, effective: 0, rejected: 0 });
  const [priceLists, setPriceLists] = useState([]);
  const [availableCustomers, setAvailableCustomers] = useState(['Tất cả']);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);

  const [customersMap, setCustomersMap] = useState({});
  const [contractsMap, setContractsMap] = useState({});

  const pendingFetches = useRef(new Set());

  const [activeStatusTab, setActiveStatusTab] = useState('Tất cả');
  const [selectedType, setSelectedType] = useState('Tất cả');
  const [selectedCustomer, setSelectedCustomer] = useState('Tất cả');
  
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const availableTypes = ['Tất cả', 'CUSTOMER', 'CONTRACT', 'GENERAL', 'SERVICE_GROUP', 'SERVICE_TYPE'];

  const extractList = (resData) => {
    if (!resData) return [];
    if (Array.isArray(resData)) return resData;
    if (Array.isArray(resData.data)) return resData.data;
    if (Array.isArray(resData.content)) return resData.content;
    if (Array.isArray(resData.items)) return resData.items;
    if (resData.data && Array.isArray(resData.data.items)) return resData.data.items;
    if (resData.data && Array.isArray(resData.data.content)) return resData.data.content;
    return [];
  };

  useEffect(() => {
    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

    fetch(`${CONTRACT_SERVICE_URL}/api/v1/customers`, { headers })
      .then(res => res.json())
      .then(resData => {
        const list = extractList(resData);
        const map = {};
        list.forEach((item) => {
          const id = String(item.customer_id || item.id || item.customerId || '').trim().toLowerCase();
          const code = String(item.customer_code || item.customerCode || item.code || '').trim();
          const name = String(item.customer_name || item.customerName || item.full_name || item.name || '').trim();
          
          if (id) map[id] = { code, name };
          if (code) map[code.toLowerCase()] = { code, name };
        });
        setCustomersMap(prev => ({ ...prev, ...map }));
      })
      .catch(err => console.error("Lỗi lấy danh sách khách hàng:", err));

    fetch(`${CONTRACT_SERVICE_URL}/api/v1/contracts`, { headers })
      .then(res => res.json())
      .then(resData => {
        const list = extractList(resData);
        const map = {};
        list.forEach((item) => {
          const id = String(item.contract_id || item.id || '').trim().toLowerCase();
          const code = String(item.contract_number || item.contract_code || item.code || '').trim();
          const name = String(item.contract_name || item.title || '').trim();
          
          if (id) map[id] = { code, name };
          if (code) map[code.toLowerCase()] = { code, name };
        });
        setContractsMap(prev => ({ ...prev, ...map }));
      })
      .catch(err => console.error("Lỗi lấy danh sách hợp đồng:", err));
  }, [token]);

  const fetchSingleItem = async (type, id) => {
    if (!id || pendingFetches.current.has(`${type}_${id}`)) return;
    pendingFetches.current.add(`${type}_${id}`);

    const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
    const endpoint = type === 'CUSTOMER' ? `customers/${id}` : `contracts/${id}`;

    try {
      const res = await fetch(`${CONTRACT_SERVICE_URL}/api/v1/${endpoint}`, { headers });
      if (!res.ok) return;
      const resData = await res.json();
      const item = resData.data || resData.item || resData;

      if (type === 'CUSTOMER') {
        const name = item.customer_name || item.customerName || item.full_name || item.name || '';
        const code = item.customer_code || item.customerCode || item.code || '';
        setCustomersMap(prev => ({ ...prev, [id.toLowerCase()]: { name, code } }));
      } else {
        const name = item.contract_name || item.title || '';
        const code = item.contract_number || item.contract_code || item.code || '';
        setContractsMap(prev => ({ ...prev, [id.toLowerCase()]: { name, code } }));
      }
    } catch (err) {
      console.error(`Lỗi fetch ${type} lẻ:`, err);
    }
  };

  const renderScopeInfo = (item, activeVersionObj) => {
    const scopeType = String(
      item.scope_type || item.scopeType || item.target_type || item.type ||
      activeVersionObj?.scope_type || activeVersionObj?.target_type || ""
    ).toUpperCase();

    const scopeId = String(
      item.scope_id || item.scopeId || item.contractId || item.targetId ||
      activeVersionObj?.scope_id || activeVersionObj?.scopeId || ""
    ).trim();

    if (!scopeId || scopeId === "null" || scopeId === "N/A" || scopeType === "GENERAL") {
      return null;
    }

    const key = scopeId.toLowerCase();

    if (scopeType === "CUSTOMER") {
      const customer = customersMap[key];
      if (customer) {
        const displayName = customer.name || customer.code;
        const showCode = customer.code && customer.code.toLowerCase() !== displayName.toLowerCase();
        return (
          <div className="mt-0.5">
            <div className="text-[11px] font-normal text-slate-400">{displayName}</div>
            {showCode && (
              <div className="text-[10px] text-slate-400">{customer.code}</div>
            )}
          </div>
        );
      }
      fetchSingleItem('CUSTOMER', scopeId);
    }

    if (scopeType === "CONTRACT") {
      const contract = contractsMap[key];
      if (contract) {
        const displayName = contract.name || contract.code;
        const showCode = contract.code && contract.code.toLowerCase() !== displayName.toLowerCase();
        return (
          <div className="mt-0.5">
            <div className="text-[11px] font-normal text-slate-400">{displayName}</div>
            {showCode && (
              <div className="text-[10px] text-slate-400">{contract.code}</div>
            )}
          </div>
        );
      }
      fetchSingleItem('CONTRACT', scopeId);
    }

    // Hiển thị tạm ID đã được rút gọn nếu đang chờ API phản hồi
    const shortId = scopeId.length > 18 ? `${scopeId.substring(0, 8)}...${scopeId.substring(scopeId.length - 4)}` : scopeId;
    return (
      <div className="mt-0.5 text-[11px] font-normal text-slate-400 font-mono">
        {shortId}
      </div>
    );
  };

  const formatVersion = (item) => {
    if (!item) return 'v1.0';

    const getVerString = (v) => {
      if (!v) return null;
      if (typeof v === 'string' || typeof v === 'number') return String(v);
      if (typeof v === 'object') return v.version_number || v.versionNumber || v.version || null;
      return null;
    };

    let raw = 
      getVerString(item.version) ||
      getVerString(item.version_number) ||
      getVerString(item.versionNumber) ||
      getVerString(item.latest_version) ||
      getVerString(item.latestVersion) ||
      getVerString(item.current_version) ||
      getVerString(item.currentVersion) ||
      getVerString(item.active_version) ||
      getVerString(item.activeVersion);

    if (!raw && Array.isArray(item.versions) && item.versions.length > 0) {
      const sortedVersions = [...item.versions].sort((a, b) => {
        const parseVer = (vObj) => {
          const vStr = String(vObj?.version_number || vObj?.version || '0');
          return vStr.replace(/[^\d.]/g, '').split('.').map(Number);
        };
        const numA = parseVer(a);
        const numB = parseVer(b);
        for (let i = 0; i < Math.max(numA.length, numB.length); i++) {
          const valA = numA[i] || 0;
          const valB = numB[i] || 0;
          if (valA !== valB) return valB - valA;
        }
        return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      });
      raw = getVerString(sortedVersions[0]);
    }

    if (!raw) return 'v1.0';

    const cleanStr = String(raw).trim();
    return cleanStr.toLowerCase().startsWith('v') ? cleanStr : `v${cleanStr}`;
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
      setPage(1);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!token) return;

    fetch(`${API_BASE_URL}/stats`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => setStats(data))
      .catch((err) => console.error('Lỗi lấy thống kê:', err));
  }, [token]);

  useEffect(() => {
    if (!token) return;
    setLoading(true);

    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });

    if (activeStatusTab !== 'Tất cả') params.append('status', activeStatusTab);
    if (selectedType !== 'Tất cả') params.append('type', selectedType);
    if (selectedCustomer !== 'Tất cả') params.append('customer', selectedCustomer);
    if (debouncedSearch.trim() !== '') params.append('search', debouncedSearch.trim());

    fetch(`${API_BASE_URL}?${params.toString()}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const listData = Array.isArray(data) ? data : (data.items || []);
        const total = data.total || data.totalItems || data.count || listData.length;

        setPriceLists(listData);
        setTotalItems(total);

        if (data.available_customers) {
          setAvailableCustomers(data.available_customers);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Lỗi lấy danh sách bảng giá:', err);
        setLoading(false);
      });
  }, [activeStatusTab, selectedType, selectedCustomer, debouncedSearch, page, token]);

  const handleFilterChange = (setter, value) => {
    setter(value);
    setPage(1);
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

  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

  return (
    <div className="space-y-4 text-slate-700 font-sans p-4">
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
                <th className="py-3 px-4">Tạo / Cập nhật bởi</th>
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
                priceLists.map((item, index) => {
                  const itemCode = item.price_list_code || item.price_code || item.id;

                  let activeVersionObj = item.latest_version || item.latestVersion || item.current_version || item.currentVersion || item.active_version || item.activeVersion;
                  
                  if (!activeVersionObj && Array.isArray(item.versions) && item.versions.length > 0) {
                    activeVersionObj = item.versions[0];
                  }

                  const itemName = 
                    (typeof activeVersionObj === 'object' ? (activeVersionObj?.price_list_name || activeVersionObj?.price_name || activeVersionObj?.name) : null) ||
                    item.price_list_name || 
                    item.price_name || 
                    item.name || 
                    'Bảng giá dịch vụ';

                  const itemType = item.target_type || item.scope_type || item.type || 'GENERAL';

                  const effectiveFrom = (typeof activeVersionObj === 'object' && activeVersionObj?.valid_from) || item.effective_from || item.valid_from;
                  const effectiveTo = (typeof activeVersionObj === 'object' && activeVersionObj?.valid_to) || item.effective_to || item.valid_to;
                  const effectiveDisplay = (effectiveFrom || effectiveTo) 
                    ? `${effectiveFrom || '...'} - ${effectiveTo || 'Vô thời hạn'}` 
                    : (item.effectiveTime || 'Vô thời hạn');

                  return (
                    <tr 
                      key={item.price_list_id || item.price_list_code || item.id || index} 
                      className="hover:bg-slate-50/70 transition"
                    >
                      <td className="py-3 px-4 font-semibold text-slate-900">{itemCode}</td>
                      <td className="py-3 px-4">
                        <div className="font-bold text-slate-800">{itemName}</div>
                        {renderScopeInfo(item, activeVersionObj)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">
                          {itemType}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-600 font-medium">
                        {formatVersion(item)}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        {effectiveDisplay}
                      </td>
                      <td className="py-3 px-4">{renderStatusBadge(item.status)}</td>
                      <td className="py-3 px-4">
                        <div className="text-slate-800 font-medium">
                          {item.updated_by || item.updatedBy || 'Staff'}
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {item.updated_at || item.updatedAt || ''}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button 
                          onClick={() => navigate(`/staff/price-lists/${item.price_list_code || itemCode}`)}
                          className="p-1 text-slate-400 hover:text-sky-600 rounded transition cursor-pointer"
                          title="Xem chi tiết"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
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