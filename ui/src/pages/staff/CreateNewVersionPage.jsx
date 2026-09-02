import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  ArrowLeft, 
  Lock, 
  Plus, 
  Trash2, 
  Loader2, 
  AlertCircle, 
  Check, 
  Send,
  Layers,
  FileText,
  DollarSign
} from 'lucide-react';

const API_BASE_URL = 'http://localhost:8082/api/v1'; 
const API_PRICE_LISTS = `${API_BASE_URL}/price-lists`;
const API_PRICE_HISTORY = `${API_BASE_URL}/price-history`;
const CONTRACT_SERVICE_URL = 'http://localhost:8083';

export default function CreateNewVersionPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  // State quản lý trạng thái tải & gửi dữ liệu
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // State thông tin phiên bản & danh mục
  const [versionsList, setVersionsList] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [selectedVersionStatus, setSelectedVersionStatus] = useState('');

  const [priceCode, setPriceCode] = useState(id || '');
  const [priceName, setPriceName] = useState('');
  const [targetType, setTargetType] = useState('CUSTOMER');
  const [specificTarget, setSpecificTarget] = useState('');
  
  // Maps lưu thông tin Khách hàng & Hợp đồng từ API port 8083
  const [customersMap, setCustomersMap] = useState({});
  const [contractsMap, setContractsMap] = useState({});

  // Thời gian của phiên bản đang chọn
  const [effectiveFrom, setEffectiveFrom] = useState('');
  const [effectiveTo, setEffectiveTo] = useState('');
  
  const [nextVersionStr, setNextVersionStr] = useState('v1.1');

  const [services, setServices] = useState([]);
  const [availableServices, setAvailableServices] = useState([]);
  
  // Cache dữ liệu đang chỉnh sửa tạm thời theo version_id
  const [draftServicesMap, setDraftServicesMap] = useState({});

  const [serviceToDelete, setServiceToDelete] = useState(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);

  // Gọi API tải danh sách Khách hàng & Hợp đồng
  useEffect(() => {
    const fetchCustomers = async () => {
      try {
        const res = await fetch(`${CONTRACT_SERVICE_URL}/api/v1/customers`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) return;
        const resData = await res.json();
        let list = [];
        if (Array.isArray(resData)) list = resData;
        else if (Array.isArray(resData?.data)) list = resData.data;
        else if (Array.isArray(resData?.content)) list = resData.content;
        else if (Array.isArray(resData?.items)) list = resData.items;

        const map = {};
        list.forEach((item) => {
          const cId = item.customer_id || item.customerId || item.id;
          const cCode = item.customer_code || item.customerCode || "";
          const cName = item.customer_name || item.customerName || item.full_name || item.name || "";
          if (cId) map[String(cId)] = { code: cCode, name: cName };
          if (cCode) map[String(cCode)] = { code: cCode, name: cName };
        });
        setCustomersMap(map);
      } catch (err) {
        console.error("Error fetching customers:", err);
      }
    };

    const fetchContracts = async () => {
      try {
        const res = await fetch(`${CONTRACT_SERVICE_URL}/api/v1/contracts`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) return;
        const resData = await res.json();
        let list = [];
        if (Array.isArray(resData)) list = resData;
        else if (Array.isArray(resData?.data)) list = resData.data;
        else if (Array.isArray(resData?.content)) list = resData.content;
        else if (Array.isArray(resData?.items)) list = resData.items;

        const map = {};
        list.forEach((item) => {
          const ctId = item.contract_id || item.id;
          const ctCode = item.contract_number || item.code || "";
          const ctName = item.contract_name || item.title || item.customer_name || "";
          if (ctId) map[String(ctId)] = { code: ctCode, name: ctName };
          if (ctCode) map[String(ctCode)] = { code: ctCode, name: ctName };
        });
        setContractsMap(map);
      } catch (err) {
        console.error("Error fetching contracts:", err);
      }
    };

    fetchCustomers();
    fetchContracts();
  }, [token]);

  // Parse thông báo lỗi từ FastAPI/Pydantic
  const parseFastAPIError = (data) => {
    if (!data) return 'Thao tác thất bại. Vui lòng kiểm tra lại!';
    
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((err) => {
          const loc = err.loc ? err.loc.filter(l => l !== 'body').join('.') : '';
          return `${loc ? `[${loc}]: ` : ''}${err.msg}`;
        })
        .join('\n');
    }
    
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.message === 'string') return data.message;
    return JSON.stringify(data);
  };

  // Utilities format ngày giờ & số tiền
  const formatDateForInput = (dateStr) => {
    if (!dateStr || dateStr === '---' || dateStr === 'null' || dateStr === 'undefined') return '';
    
    if (Array.isArray(dateStr)) {
      const [year, month, day] = dateStr;
      return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }

    const str = String(dateStr).trim();
    if (str.includes('T')) return str.split('T')[0];
    if (str.includes('/')) {
      const parts = str.split('/');
      if (parts.length === 3) {
        return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
      }
    }
    return str;
  };

  const formatDateForDisplay = (dateStr) => {
    if (!dateStr || dateStr === '---' || dateStr === 'null') return 'Chưa xác định';
    
    if (Array.isArray(dateStr)) {
      const [year, month, day] = dateStr;
      return `${String(day).padStart(2, '0')}/${String(month).padStart(2, '0')}/${year}`;
    }

    const str = String(dateStr).trim();
    const datePart = str.includes('T') ? str.split('T')[0] : str;
    
    if (datePart.includes('-')) {
      const [year, month, day] = datePart.split('-');
      return `${day}/${month}/${year}`;
    }
    return dateStr;
  };

  const formatNumberWithDots = (val) => {
    if (val === undefined || val === null || val === '') return '';
    const rawNumber = String(val).replace(/\D/g, '');
    if (!rawNumber) return '';
    return Number(rawNumber).toLocaleString('vi-VN');
  };

  const parseNumberFromDots = (val) => {
    if (!val) return 0;
    const rawNumber = String(val).replace(/\D/g, '');
    return rawNumber ? Number(rawNumber) : 0;
  };

  // Hàm tính phiên bản kế tiếp dự trên danh sách tất cả phiên bản hiện có
  const calculateNextVersionFromList = (list) => {
    if (!list || list.length === 0) return 'v1.1';
    
    let maxMajor = 1;
    let maxMinor = 0;

    list.forEach((v) => {
      const verStr = String(v.version_number || v.version || '1.0').replace(/^v/i, '');
      const parts = verStr.split('.');
      if (parts.length >= 2) {
        const major = parseInt(parts[0], 10) || 1;
        const minor = parseInt(parts[1], 10) || 0;
        if (major > maxMajor || (major === maxMajor && minor > maxMinor)) {
          maxMajor = major;
          maxMinor = minor;
        }
      }
    });

    return `v${maxMajor}.${maxMinor + 1}`;
  };

  // Helper lấy tên chuẩn cho Version
  const extractVersionName = (obj) => {
    if (!obj) return '';
    return (
      obj.price_list_name ||
      obj.price_name ||
      obj.priceName ||
      obj.version_price_name ||
      obj.versionPriceName ||
      obj.version_name ||
      obj.versionName ||
      obj.name ||
      ''
    );
  };

  // Helper hiển thị tên Khách hàng / Hợp đồng đã map (Đã xóa bỏ ngoặc mở/đóng)
  const getMappedScopeTargetDisplay = (type, targetVal) => {
    if (!targetVal) return '';
    const tType = String(type || '').toUpperCase();
    const key = String(targetVal);

    if (tType === 'GENERAL') {
      return 'Áp dụng cho tất cả (Chung)';
    }

    if (tType === 'CUSTOMER') {
      const found = customersMap[key];
      if (found) {
        return found.name ? `${found.name} - ${found.code || key}` : (found.code || key);
      }
    } else if (tType === 'CONTRACT') {
      const found = contractsMap[key];
      if (found) {
        return found.code ? `${found.code} - ${found.name}` : found.name;
      }
    }

    return targetVal;
  };

  // Mapping danh sách dịch vụ
  const mapRawDetailsToServices = (rawDetails, catalog) => {
    return rawDetails.map((s) => {
      const sId = String(s.service_item_id || s.serviceItemId || s.service_id || s.id || '');
      const matched = catalog.find(
        (c) => String(c.id || c.serviceItemId || c.service_item_id || c.serviceCode || c.code) === sId
      );

      return {
        detailId: s.id || s.detailId || null,
        serviceItemId: sId,
        serviceCode: s.service_code || s.serviceCode || matched?.service_code || matched?.serviceCode || '',
        serviceName: s.service_name || s.serviceName || s.name || matched?.service_name || matched?.serviceName || '',
        unit: s.unit || matched?.unit || 'Lượt',
        price: s.unit_price !== undefined ? s.unit_price : (s.unitPrice !== undefined ? s.unitPrice : (s.price || 0)),
      };
    });
  };

  // Tải chi tiết 1 phiên bản
  const fetchVersionDetails = async (versionId, verObj, catalogList) => {
    try {
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      let res = await fetch(`${API_PRICE_HISTORY}/versions/${versionId}/details`, { headers });
      if (!res.ok && priceCode) {
        res = await fetch(`${API_PRICE_HISTORY}/price-lists/${priceCode}/versions/${versionId}`, { headers });
      }

      if (!res.ok) throw new Error('Không thể tải chi tiết phiên bản');

      const responseData = await res.json();
      const detailsData = responseData.data || responseData;

      // Đọc tên chính xác của Version hiện tại
      const currentVerName = extractVersionName(detailsData) || extractVersionName(verObj);
      if (currentVerName) {
        setPriceName(currentVerName);
      }

      setEffectiveFrom(formatDateForInput(verObj?.valid_from || verObj?.validFrom || detailsData.valid_from || detailsData.effectiveFrom));
      setEffectiveTo(formatDateForInput(verObj?.valid_to || verObj?.validTo || detailsData.valid_to || detailsData.effectiveTo));

      // Kiểm tra cache nháp
      if (draftServicesMap[versionId]) {
        setServices(draftServicesMap[versionId]);
        return;
      }

      let rawDetails = [];
      if (Array.isArray(detailsData)) rawDetails = detailsData;
      else if (Array.isArray(detailsData.details)) rawDetails = detailsData.details;
      else if (Array.isArray(detailsData.services)) rawDetails = detailsData.services;
      else if (Array.isArray(detailsData.items)) rawDetails = detailsData.items;

      const mappedServices = mapRawDetailsToServices(rawDetails, catalogList);
      setServices(mappedServices);
    } catch (err) {
      console.error('Lỗi tải chi tiết phiên bản:', err);
    }
  };

  // Initial Fetch Data
  useEffect(() => {
    let isMounted = true;

    const fetchInitialData = async () => {
      setLoading(true);
      setError(null);
      try {
        const headers = {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        };

        // 1. Tải danh mục Dịch vụ
        let catalogList = [];
        const srvRes = await fetch(`${API_PRICE_LISTS}/services`, { headers });
        if (srvRes.ok) {
          const srvData = await srvRes.json();
          catalogList = Array.isArray(srvData) ? srvData : (srvData.content || srvData.data || []);
          if (isMounted) setAvailableServices(catalogList);
        }

        // 2. Tải danh sách các phiên bản
        const verRes = await fetch(`${API_PRICE_HISTORY}/price-lists/${id}/versions`, { headers });
        let versionsData = [];
        if (verRes.ok) {
          const rawVer = await verRes.json();
          versionsData = Array.isArray(rawVer) ? rawVer : (rawVer.data || []);
          if (isMounted) {
            setVersionsList(versionsData);
            // Tính số phiên bản dự kiến chuẩn xác dựa trên toàn bộ danh sách phiên bản hiện có
            setNextVersionStr(calculateNextVersionFromList(versionsData));
          }
        }

        // 3. Tải thông tin chung Bảng giá
        let priceListInfo = null;
        const mainRes = await fetch(`${API_PRICE_LISTS}/${id}`, { headers });
        if (mainRes.ok) {
          const mainData = await mainRes.json();
          priceListInfo = mainData.price_list || mainData;
          if (isMounted) {
            setPriceCode(priceListInfo.price_list_code || priceListInfo.priceCode || id);
            setTargetType(priceListInfo.type || priceListInfo.target_type || priceListInfo.targetType || 'CUSTOMER');
            setSpecificTarget(
              priceListInfo.contract_id ||
              priceListInfo.contractId ||
              priceListInfo.customer_id ||
              priceListInfo.customerId ||
              priceListInfo.specific_target ||
              priceListInfo.scope_id ||
              ''
            );
          }
        }

        // 4. Ưu tiên chọn phiên bản SUBMITTED/DRAFT hoặc EFFECTIVE
        const activeVer = versionsData.find(v => v.status === 'SUBMITTED' || v.status === 'DRAFT') || 
                          versionsData.find(v => v.status === 'EFFECTIVE') || 
                          versionsData[0];
        
        if (isMounted) {
          const initialName = extractVersionName(activeVer) || extractVersionName(priceListInfo);
          setPriceName(initialName);
        }

        if (activeVer && isMounted) {
          const vId = activeVer.id || activeVer.version_id;
          setSelectedVersionId(vId);
          setSelectedVersionStatus(activeVer.status || '');
          await fetchVersionDetails(vId, activeVer, catalogList);
        }

      } catch (err) {
        if (isMounted) setError(err.message || 'Có lỗi xảy ra khi khởi tạo dữ liệu');
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    if (id) fetchInitialData();

    return () => {
      isMounted = false;
    };
  }, [id, token]);

  // Chọn Version ở danh sách Lịch sử
  const handleSelectVersionItem = async (ver) => {
    const vId = ver.id || ver.version_id;
    
    if (selectedVersionId) {
      setDraftServicesMap((prev) => ({
        ...prev,
        [selectedVersionId]: services,
      }));
    }

    setSelectedVersionId(vId);
    setSelectedVersionStatus(ver.status || '');
    setLoading(true);
    await fetchVersionDetails(vId, ver, availableServices);
    setLoading(false);
  };

  // Cập nhật ô nhập thông tin dịch vụ
  const handleServiceChange = (index, field, value) => {
    setServices((prev) => {
      const updated = [...prev];
      updated[index] = {
        ...updated[index],
        [field]: field === 'price' ? parseNumberFromDots(value) : value,
      };

      if (selectedVersionId) {
        setDraftServicesMap((dMap) => ({
          ...dMap,
          [selectedVersionId]: updated,
        }));
      }

      return updated;
    });
  };

  // Thay đổi dịch vụ được chọn từ Dropdown
  const handleSelectServiceChange = (index, selectedItemId) => {
    const foundObj = availableServices.find(
      (s) => String(s.id || s.serviceItemId || s.service_item_id || s.serviceCode || s.code) === String(selectedItemId)
    );

    setServices((prev) => {
      const updated = [...prev];
      if (foundObj) {
        updated[index] = {
          ...updated[index],
          serviceItemId: String(foundObj.id || foundObj.serviceItemId || selectedItemId),
          serviceCode: foundObj.service_code || foundObj.serviceCode || foundObj.code || '',
          serviceName: foundObj.service_name || foundObj.serviceName || foundObj.name || '',
          unit: foundObj.unit || updated[index]?.unit || 'Lượt',
        };
      } else {
        updated[index] = {
          ...updated[index],
          serviceItemId: selectedItemId,
          serviceCode: '',
          serviceName: '',
          unit: 'Lượt',
        };
      }

      if (selectedVersionId) {
        setDraftServicesMap((dMap) => ({
          ...dMap,
          [selectedVersionId]: updated,
        }));
      }

      return updated;
    });
  };

  const handleAddService = () => {
    setServices((prev) => {
      const updated = [
        ...prev,
        { detailId: null, serviceItemId: '', serviceCode: '', serviceName: '', unit: 'Lượt', price: 0 }
      ];
      if (selectedVersionId) {
        setDraftServicesMap((dMap) => ({ ...dMap, [selectedVersionId]: updated }));
      }
      return updated;
    });
  };

  const confirmDeleteService = () => {
    if (serviceToDelete === null) return;
    setServices((prev) => {
      const updated = prev.filter((_, i) => i !== serviceToDelete.index);
      if (selectedVersionId) {
        setDraftServicesMap((dMap) => ({ ...dMap, [selectedVersionId]: updated }));
      }
      return updated;
    });
    setServiceToDelete(null);
  };

  // Submit dữ liệu
  const handleSubmitApproval = async () => {
    if (selectedVersionStatus !== 'EFFECTIVE') return;

    const validServices = services
      .filter((s) => s.serviceItemId && String(s.serviceItemId).trim() !== '')
      .map((s) => {
        const itemPrice = Number(s.price) || 0;
        return {
          service_item_id: s.serviceItemId,
          serviceItemId: s.serviceItemId,
          price: itemPrice,
          unit_price: itemPrice,
          unitPrice: itemPrice,
          service_code: s.serviceCode || '',
          service_name: s.serviceName || '',
          unit: s.unit || 'Lượt',
        };
      });

    if (validServices.length === 0) {
      alert('Vui lòng chọn ít nhất 1 dịch vụ hợp lệ trước khi gửi phê duyệt!');
      return;
    }

    if (!effectiveFrom) {
      alert('Vui lòng nhập Ngày bắt đầu hiệu lực!');
      return;
    }

    setSubmitting(true);
    try {
      const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      };

      const payload = {
        price_list_name: priceName,
        price_name: priceName,
        priceName: priceName,
        target_type: targetType || 'CUSTOMER',
        targetType: targetType || 'CUSTOMER',
        valid_from: effectiveFrom,
        validFrom: effectiveFrom,
        effectiveFrom: effectiveFrom,
        valid_to: effectiveTo || null,
        validTo: effectiveTo || null,
        effectiveTo: effectiveTo || null,
        services: validServices,
      };

      let res = await fetch(`${API_PRICE_LISTS}/${encodeURIComponent(priceCode)}/create-version`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        const errorMessage = parseFastAPIError(errData);
        throw new Error(errorMessage);
      }

      setShowSubmitModal(true);
    } catch (err) {
      alert(`Thao tác thất bại:\n${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const renderStatusBadge = (status) => {
    const s = String(status || '').toUpperCase();
    switch (s) {
      case 'DRAFT':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">DRAFT</span>;
      case 'SUBMITTED':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">SUBMITTED</span>;
      case 'EFFECTIVE':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">EFFECTIVE</span>;
      case 'SUPERSEDED':
      case 'SUP':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">SUPERSEDED</span>;
      case 'REJECTED':
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 text-rose-700 border border-rose-200">REJECTED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600 border border-slate-200">{s || 'N/A'}</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-[600px] flex flex-col items-center justify-center space-y-4 text-slate-500 font-sans">
        <div className="p-4 bg-teal-50 rounded-full">
          <Loader2 className="w-8 h-8 animate-spin text-[#2b727d]" />
        </div>
        <span className="text-sm font-medium text-slate-600">Đang truy vấn dữ liệu từ API...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-8 rounded-2xl border border-slate-200 text-center space-y-4 max-w-lg mx-auto mt-12 shadow-sm font-sans">
        <div className="w-12 h-12 bg-rose-50 rounded-full flex items-center justify-center mx-auto text-rose-500">
          <AlertCircle className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h2 className="text-base font-bold text-slate-800">Lỗi kết nối API</h2>
          <p className="text-xs text-slate-500 max-w-xs mx-auto whitespace-pre-line">{error}</p>
        </div>
        <button
          onClick={() => navigate('/staff/price-lists')}
          className="px-4 py-2 bg-[#2b727d] text-white rounded-xl text-xs font-semibold hover:bg-[#235d67] transition cursor-pointer"
        >
          Quay lại danh sách
        </button>
      </div>
    );
  }

  const isEffective = selectedVersionStatus === 'EFFECTIVE';

  return (
    <div className="space-y-6 text-slate-700 font-sans max-w-[1400px] mx-auto pb-12">
      {/* HEADER */}
      <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-xs flex items-center space-x-4">
        <button
          onClick={() => navigate('/staff/price-lists')}
          className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-slate-600 hover:bg-slate-100 transition cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-lg font-bold text-slate-900">Tạo phiên bản đơn giá mới</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-teal-50 text-[#2b727d] border border-teal-200">
              {priceCode}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cấu hình danh mục các hạng mục dịch vụ cho phiên bản kế tiếp.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* SIDEBAR LỊCH SỬ PHIÊN BẢN */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-slate-200/80 p-5 space-y-4 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div className="flex items-center space-x-2">
              <Layers className="w-4 h-4 text-[#2b727d]" />
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider">Lịch sử phiên bản</h2>
            </div>
            <span className="text-[11px] font-medium text-slate-400">{versionsList.length} bản ghi</span>
          </div>

          <div className="space-y-2.5 max-h-[520px] overflow-y-auto pr-1">
            {versionsList.map((ver, idx) => {
              const vId = ver.id || ver.version_id || idx;
              const isSelected = selectedVersionId === vId;
              
              const rawVer = ver.version_number || ver.version || '1.0';
              const verNum = String(rawVer).toLowerCase().startsWith('v') ? rawVer : `v${rawVer}`;
              const verTitle = extractVersionName(ver);

              return (
                <div
                  key={vId}
                  onClick={() => handleSelectVersionItem(ver)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start space-x-3 ${
                    isSelected
                      ? 'border-[#2b727d] bg-teal-50/30 ring-1 ring-[#2b727d]/20'
                      : 'border-slate-100 bg-slate-50/50 hover:bg-slate-50'
                  }`}
                >
                  <div className={`mt-0.5 w-4 h-4 rounded-md flex items-center justify-center ${isSelected ? 'bg-[#2b727d] text-white' : 'border border-slate-300'}`}>
                    {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-bold ${isSelected ? 'text-[#2b727d]' : 'text-slate-800'}`}>
                        {verNum}
                      </span>
                      {renderStatusBadge(ver.status)}
                    </div>
                    {verTitle && (
                      <p className="text-[11px] font-medium text-slate-700 truncate max-w-[200px]">
                        {verTitle}
                      </p>
                    )}
                    <div className="text-[11px] text-slate-500 flex justify-between">
                      <span>Từ: {formatDateForDisplay(ver.valid_from || ver.validFrom)}</span>
                      <span>Đến: {formatDateForDisplay(ver.valid_to || ver.validTo)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* BẢNG CẤU HÌNH DỊCH VỤ */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-6 shadow-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-800">Cấu hình phiên bản đang tạo</h2>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-3 py-1 rounded-lg text-xs font-bold bg-teal-50 text-[#2b727d] border border-teal-200">
                Phiên bản dự kiến: {nextVersionStr}
              </span>
              {renderStatusBadge(selectedVersionStatus || 'DRAFT')}
            </div>
          </div>

          {/* FORM THÔNG TIN CHUNG */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-2">
              <FileText className="w-3.5 h-3.5 text-[#2b727d]" />
              <span>1. Thông tin chung bảng giá</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <label className="block text-slate-600 font-medium mb-1">Mã bảng giá</label>
                <div className="relative">
                  <input
                    type="text"
                    readOnly
                    value={priceCode}
                    className="w-full pl-3 pr-8 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 font-mono font-medium focus:outline-none cursor-not-allowed"
                  />
                  <Lock className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-3" />
                </div>
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Tên phiên bản / Bảng giá</label>
                <input
                  type="text"
                  value={priceName}
                  onChange={(e) => setPriceName(e.target.value)}
                  placeholder="Nhập tên riêng cho phiên bản mới..."
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-800 font-medium focus:outline-none focus:border-[#2b727d] transition"
                />
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Scope ID / Hợp đồng</label>
                <div className="relative">
                  <input
                    type="text"
                    readOnly
                    value={getMappedScopeTargetDisplay(targetType, specificTarget)}
                    className="w-full pl-3 pr-8 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-500 font-mono text-xs focus:outline-none cursor-not-allowed"
                  />
                  <Lock className="w-3.5 h-3.5 text-slate-400 absolute right-3 top-3" />
                </div>
              </div>

              <div>
                <label className="block text-slate-600 font-medium mb-1">Thời gian hiệu lực</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="date"
                    value={effectiveFrom}
                    onChange={(e) => setEffectiveFrom(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-xs focus:outline-none focus:border-[#2b727d]"
                  />
                  <input
                    type="date"
                    value={effectiveTo}
                    onChange={(e) => setEffectiveTo(e.target.value)}
                    className="w-full px-2.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-xs focus:outline-none focus:border-[#2b727d]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* DANH SÁCH CHI TIẾT DỊCH VỤ */}
          <div className="space-y-4 pt-2 border-t border-slate-100">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center space-x-2">
                <DollarSign className="w-3.5 h-3.5 text-[#2b727d]" />
                <span>2. Danh sách dịch vụ áp dụng</span>
              </h3>

              <button
                type="button"
                onClick={handleAddService}
                className="px-3 py-1.5 rounded-xl border border-teal-200 bg-teal-50 hover:bg-teal-100 text-[#2b727d] text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dòng mới</span>
              </button>
            </div>

            <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-semibold">
                    <th className="py-3 px-3 w-[5%] text-center">STT</th>
                    <th className="py-3 px-3 w-[35%]">Dịch vụ cung cấp</th>
                    <th className="py-3 px-3 w-[18%]">Mã dịch vụ</th>
                    <th className="py-3 px-3 w-[14%]">Đơn vị</th>
                    <th className="py-3 px-3 w-[20%] text-right">Đơn giá định mức</th>
                    <th className="py-3 px-3 w-[8%] text-center">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {services.length > 0 ? (
                    services.map((srv, index) => (
                      <tr key={index} className="hover:bg-slate-50/50 transition">
                        <td className="py-2.5 px-3 text-center text-slate-400 font-mono text-[11px]">
                          {index + 1}
                        </td>
                        
                        <td className="py-2.5 px-3">
                          <select
                            value={srv.serviceItemId}
                            onChange={(e) => handleSelectServiceChange(index, e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-[#2b727d] bg-white text-slate-800 font-medium text-xs"
                          >
                            <option value="">-- Chọn dịch vụ --</option>
                            {availableServices.map((s, idx) => {
                              const itemId = String(s.id || s.serviceItemId || s.service_item_id || s.serviceCode || s.code);
                              const name = s.service_name || s.serviceName || s.name;
                              const code = s.service_code || s.serviceCode || s.code;
                              return (
                                <option key={idx} value={itemId}>
                                  {name} ({code})
                                </option>
                              );
                            })}
                          </select>
                        </td>

                        <td className="py-2.5 px-3 font-mono text-slate-400">
                          <input
                            type="text"
                            readOnly
                            value={srv.serviceCode}
                            placeholder="Mã dịch vụ..."
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-100 bg-slate-50/80 text-slate-500 font-mono text-xs cursor-default"
                          />
                        </td>

                        <td className="py-2.5 px-3">
                          <input
                            type="text"
                            value={srv.unit}
                            onChange={(e) => handleServiceChange(index, 'unit', e.target.value)}
                            placeholder="VD: Lượt"
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-[#2b727d] text-xs text-slate-700"
                          />
                        </td>

                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end space-x-1.5">
                            <input
                              type="text"
                              value={formatNumberWithDots(srv.price)}
                              onChange={(e) => handleServiceChange(index, 'price', e.target.value)}
                              className="w-32 px-2.5 py-1.5 rounded-lg border border-slate-200 text-right font-bold text-slate-800 focus:outline-none focus:border-[#2b727d] transition"
                            />
                            <span className="text-[10px] font-semibold text-slate-400 select-none">VND</span>
                          </div>
                        </td>

                        <td className="py-2.5 px-3 text-center">
                          <button
                            type="button"
                            onClick={() => setServiceToDelete({ index })}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition cursor-pointer"
                            title="Xóa dòng"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="py-10 text-center text-slate-400 text-xs bg-slate-50/30">
                        Chưa có hạng mục dịch vụ nào. Nhấn nút "Thêm dòng mới" để tạo.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* NÚT THAO TÁC */}
          <div className="pt-4 border-t border-slate-100 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={() => navigate('/staff/price-lists')}
              className="px-5 py-2.5 rounded-xl border border-slate-200 bg-white text-xs font-semibold text-slate-600 hover:bg-slate-50 transition cursor-pointer"
            >
              Hủy bỏ
            </button>

            <button
              type="button"
              disabled={submitting || !isEffective}
              title={!isEffective ? 'Chỉ có thể tạo phiên bản mới từ phiên bản EFFECTIVE' : ''}
              onClick={handleSubmitApproval}
              className={`px-6 py-2.5 rounded-xl bg-[#2b727d] text-white text-xs font-semibold flex items-center space-x-2 shadow-xs transition ${
                !isEffective
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-[#235d67] cursor-pointer'
              }`}
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
              <span>Lưu & Gửi phê duyệt</span>
            </button>
          </div>

        </div>
      </div>

      {/* MODAL XÁC NHẬN XÓA */}
      {serviceToDelete !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-2xl text-center space-y-4 border border-slate-100">
            <div className="w-12 h-12 bg-rose-50 text-rose-500 rounded-full flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h3 className="text-base font-bold text-slate-800">Xóa dịch vụ khỏi bản nháp?</h3>
              <p className="text-xs text-slate-500">
                Dịch vụ sẽ bị loại bỏ khỏi danh sách trước khi gửi duyệt.
              </p>
            </div>

            <div className="pt-2 flex items-center space-x-3">
              <button
                onClick={() => setServiceToDelete(null)}
                className="w-1/2 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-xl cursor-pointer"
              >
                Hủy
              </button>
              <button
                onClick={confirmDeleteService}
                className="w-1/2 py-2 px-3 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-xl cursor-pointer"
              >
                Xác nhận
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL THÀNH CÔNG */}
      {showSubmitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full shadow-2xl text-center space-y-4">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mx-auto border border-emerald-100">
              <Check className="w-8 h-8 stroke-[2.5]" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-bold text-slate-900">Gửi phê duyệt thành công!</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Phiên bản đơn giá mới đã được khởi tạo/cập nhật thành công và chuyển sang trạng thái chờ phê duyệt.
              </p>
            </div>
            <button
              onClick={() => {
                setShowSubmitModal(false);
                navigate('/staff/price-lists');
              }}
              className="w-full py-2.5 bg-[#2b727d] text-white rounded-xl text-xs font-semibold hover:bg-[#235d67] transition cursor-pointer"
            >
              Quay lại danh sách
            </button>
          </div>
        </div>
      )}
    </div>
  );
}