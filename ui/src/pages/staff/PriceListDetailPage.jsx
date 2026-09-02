import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { ArrowLeft, Clock, Loader2, AlertCircle, Plus, Trash2, Send, Check, AlertTriangle, History, Archive, CalendarX } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8082/api/v1/price-lists';
const APPROVAL_BASE_URL = 'http://localhost:8082/api/v1/approvals';
const CUSTOMER_SERVICE_URL = 'http://localhost:8083';

export default function PriceListDetailPage() {
  const { id } = useParams(); 
  const [searchParams, setSearchParams] = useSearchParams();
  
  const versionParam = searchParams.get('version_id') || searchParams.get('version');
  
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const [priceDetail, setPriceDetail] = useState(null);
  const [versionsList, setVersionsList] = useState([]);
  const [availableServices, setAvailableServices] = useState([]);
  const [targetOptions, setTargetOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [showUpdateSuccessModal, setShowUpdateSuccessModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  const [serviceToDeleteIndex, setServiceToDeleteIndex] = useState(null);

  const formatDateForInput = (dateStr) => {
    if (!dateStr) return '';
    const str = String(dateStr).trim();
    if (str.includes('T')) {
      return str.split('T')[0];
    }
    if (str.includes('/')) {
      const parts = str.split('/');
      if (parts.length === 3) {
        return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`;
      }
    }
    return str;
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

  // 1. Lấy danh sách dịch vụ có sẵn & Danh sách các phiên bản
  useEffect(() => {
    fetch(`${API_BASE_URL}/services`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error('Không thể lấy danh sách dịch vụ');
        return res.json();
      })
      .then((data) => {
        setAvailableServices(Array.isArray(data) ? data : data.content || []);
      })
      .catch((err) => console.error('Lỗi lấy danh sách dịch vụ:', err));

    if (id) {
      fetch(`${APPROVAL_BASE_URL}/${id}/versions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })
        .then((res) => res.ok ? res.json() : [])
        .then((data) => {
          if (Array.isArray(data)) {
            setVersionsList(data);
          }
        })
        .catch((err) => console.error('Lỗi lấy danh sách phiên bản:', err));
    }
  }, [id, token]);

  // 2. Lấy danh sách đối tượng áp dụng từ API /api/v1/customers hoặc contracts
  useEffect(() => {
    if (!priceDetail?.targetType || priceDetail.targetType === 'GENERAL') {
      setTargetOptions([]);
      return;
    }

    const fetchTargets = async () => {
      try {
        const isCustomer = priceDetail.targetType === 'CUSTOMER';
        const endpoint = isCustomer 
          ? `${CUSTOMER_SERVICE_URL}/api/v1/customers` 
          : `${CUSTOMER_SERVICE_URL}/api/v1/contracts`;

        const response = await fetch(endpoint, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) return;

        const resData = await response.json();
        let list = [];
        if (Array.isArray(resData)) list = resData;
        else if (Array.isArray(resData?.data)) list = resData.data;
        else if (Array.isArray(resData?.content)) list = resData.content;
        else if (Array.isArray(resData?.items)) list = resData.items;

        const formatted = list.map((item) => {
          if (isCustomer) {
            return {
              id: item.customer_id || item.customerId || item.id,
              code: item.customer_code || item.customerCode || item.code || '',
              companyName: item.company_name || item.companyName || '',
              representativeName: item.representative_name || item.representativeName || '',
              taxCode: item.tax_code || item.taxCode || '',
              email: item.email || '',
              phone: item.phone || '',
              address: item.address || '',
              name: item.company_name || item.customer_code || 'Khách hàng'
            };
          } else {
            const contractCode = item.contract_number || item.contractCode || item.code;
            return {
              id: item.contract_id || item.id,
              code: contractCode || item.contract_name || item.title || item.id,
              name: item.contract_name || item.title || 'Hợp đồng'
            };
          }
        });

        const uniqueTargets = formatted.filter(
          (item, index, self) => index === self.findIndex((t) => String(t.id) === String(item.id))
        );

        setTargetOptions(uniqueTargets);
      } catch (error) {
        console.error('Lỗi khi nạp danh sách đối tượng:', error);
      }
    };

    fetchTargets();
  }, [priceDetail?.targetType, token]);

  // Tìm thông tin chi tiết đối tượng được chọn
  const selectedTargetObj = React.useMemo(() => {
    if (!priceDetail?.specificTarget || !targetOptions.length) return null;
    return targetOptions.find(
      (item) => String(item.id) === String(priceDetail.specificTarget) || String(item.code) === String(priceDetail.specificTarget)
    );
  }, [priceDetail?.specificTarget, targetOptions]);

  // 3. Lấy chi tiết bảng giá theo price_code và version
  const fetchDetail = () => {
    if (!id) return;
    setLoading(true);
    setError(null);

    const queryParams = versionParam 
      ? `?version_id=${encodeURIComponent(versionParam)}&version=${encodeURIComponent(versionParam)}` 
      : '';

    const requestUrl = `${API_BASE_URL}/${id}${queryParams}`;
    const fallbackUrl = `${APPROVAL_BASE_URL}/${id}${queryParams}`;

    fetch(requestUrl, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    })
      .then((res) => {
        if (!res.ok && res.status === 404) {
          return fetch(fallbackUrl, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          }).then((fallbackRes) => {
            if (!fallbackRes.ok) {
              throw new Error(`Không thể lấy thông tin chi tiết (Mã lỗi: ${fallbackRes.status})`);
            }
            return fallbackRes.json();
          });
        }
        if (!res.ok) {
          throw new Error(`Không thể lấy thông tin chi tiết (Mã lỗi: ${res.status})`);
        }
        return res.json();
      })
      .then((data) => {
        const latestVerObj = data.latest_version || data.current_version || data.latestVersion || {};
        
        const rawFrom = data.effectiveFrom || data.effective_from || data.validFrom || data.valid_from || latestVerObj.valid_from || '';
        const rawTo = data.effectiveTo || data.effective_to || data.validTo || data.valid_to || latestVerObj.valid_to || '';

        const rawStatus = data.status || latestVerObj.status || data.version_status || 'DRAFT';
        const rawVersion = data.version || data.version_number || latestVerObj.version_number || '1.0';

        const rawReason = 
          data.rejectReason || 
          data.rejectionReason || 
          data.rejectedReason || 
          data.rejected_reason || 
          data.rejection_reason || 
          latestVerObj.rejected_reason || 
          latestVerObj.rejection_reason || 
          latestVerObj.rejectReason || '';

        setPriceDetail({
          priceCode: data.priceCode || data.price_code || data.priceListCode || data.id || id,
          priceName: data.priceName || data.price_name || '',
          targetType: data.targetType || data.target_type || data.scopeType || data.scope_type || 'CUSTOMER',
          specificTarget: data.specificTarget || data.specific_target || data.scopeId || data.scope_id || '',
          effectiveFrom: formatDateForInput(rawFrom),
          effectiveTo: formatDateForInput(rawTo),
          version: String(rawVersion).startsWith('v') ? rawVersion : `v${rawVersion}`,
          status: String(rawStatus).toUpperCase(),
          rejectionReason: rawReason,
          services: (data.services || latestVerObj.services || []).map((srv) => ({
            serviceCode: srv.serviceCode || srv.service_code || srv.code || '',
            serviceName: srv.serviceName || srv.service_name || srv.name || '',
            unit: srv.unit || '',
            price: srv.price || srv.unit_price || srv.unitPrice || 0,
          })),
        });
        setLoading(false);
      })
      .catch((err) => {
        console.error('Lỗi API:', err);
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchDetail();
  }, [id, versionParam, token]);

  const isSubmittedSuccess = showSuccessModal || showUpdateSuccessModal;
  const canEdit = (priceDetail?.status === 'DRAFT' || priceDetail?.status === 'REJECTED') && !isSubmittedSuccess;

  const handleInputChange = (field, value) => {
    setPriceDetail((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleVersionSelectChange = (e) => {
    const selectedVerValue = e.target.value;
    if (selectedVerValue) {
      const targetVer = versionsList.find(
        (v) => String(v.version) === String(selectedVerValue) || String(v.version_number) === String(selectedVerValue) || String(v.id) === String(selectedVerValue)
      );
      const versionIdToSend = targetVer?.id || targetVer?.version_id || selectedVerValue;
      setSearchParams({ version: selectedVerValue, version_id: versionIdToSend });
    } else {
      setSearchParams({});
    }
  };

  const handleSelectServiceChange = (index, selectedCode) => {
    const selectedObj = availableServices.find(
      (s) => (s.serviceCode || s.code) === selectedCode
    );

    setPriceDetail((prev) => {
      const newServices = [...prev.services];
      if (selectedObj) {
        newServices[index] = {
          ...newServices[index],
          serviceCode: selectedObj.serviceCode || selectedObj.code || '',
          serviceName: selectedObj.serviceName || selectedObj.name || '',
          unit: selectedObj.unit || newServices[index].unit || '',
        };
      } else {
        newServices[index] = {
          ...newServices[index],
          serviceCode: selectedCode,
        };
      }
      return { ...prev, services: newServices };
    });
  };

  const handleServiceChange = (index, field, value) => {
    setPriceDetail((prev) => {
      const newServices = [...prev.services];
      newServices[index] = {
        ...newServices[index],
        [field]: field === 'price' ? parseNumberFromDots(value) : value,
      };
      return { ...prev, services: newServices };
    });
  };

  const handleAddService = () => {
    setPriceDetail((prev) => ({
      ...prev,
      services: [
        ...prev.services,
        { serviceCode: '', serviceName: '', unit: '', price: 0 },
      ],
    }));
  };

  const handleRemoveServiceClick = (index) => {
    setServiceToDeleteIndex(index);
  };

  const confirmRemoveService = () => {
    if (serviceToDeleteIndex !== null) {
      setPriceDetail((prev) => ({
        ...prev,
        services: prev.services.filter((_, i) => i !== serviceToDeleteIndex),
      }));
      setServiceToDeleteIndex(null);
    }
  };

  const handleSaveUpdate = async () => {
    setSaving(true);
    try {
      const targetStatus = priceDetail.status === 'REJECTED' ? 'DRAFT' : priceDetail.status;

      const payload = {
        price_code: priceDetail.priceCode,
        price_name: priceDetail.priceName,
        target_type: priceDetail.targetType,
        specific_target: priceDetail.specificTarget,
        effective_from: priceDetail.effectiveFrom,
        effective_to: priceDetail.effectiveTo,
        status: targetStatus,
        version: priceDetail.version,
        services: (priceDetail.services || []).map((s) => ({
          service_code: s.serviceCode || '',
          service_name: s.serviceName || '',
          unit: s.unit || '',
          price: Number(s.price) || 0,
        })),
      };

      const response = await fetch(`${API_BASE_URL}/${priceDetail.priceCode}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        let errorMessage = 'Lỗi khi cập nhật!';
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map((e) => `${e.loc ? e.loc.join(' -> ') : ''}: ${e.msg}`)
            .join('\n');
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        }
        throw new Error(errorMessage);
      }

      if (versionParam) {
        navigate(`/staff/price-lists/${id}`, { replace: true });
      } else {
        fetchDetail();
      }

      setShowUpdateSuccessModal(true);
    } catch (err) {
      alert(`Cập nhật thất bại:\n${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitApproval = async () => {
    setSubmitting(true);
    try {
      const payload = {
        price_code: priceDetail.priceCode,
        price_name: priceDetail.priceName,
        target_type: priceDetail.targetType,
        specific_target: priceDetail.specificTarget,
        effective_from: priceDetail.effectiveFrom,
        effective_to: priceDetail.effectiveTo,
        status: 'SUBMITTED',
        services: (priceDetail.services || []).map((s) => ({
          service_code: s.serviceCode || '',
          service_name: s.serviceName || '',
          unit: s.unit || '',
          price: Number(s.price) || 0,
        })),
      };

      const response = await fetch(`${API_BASE_URL}/${priceDetail.priceCode}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorData = await response.json();
        let errorMessage = 'Không thể gửi phê duyệt!';
        if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail
            .map((e) => `${e.loc ? e.loc.join(' -> ') : ''}: ${e.msg}`)
            .join('\n');
        } else if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        }
        throw new Error(errorMessage);
      }

      setPriceDetail((prev) => ({
        ...prev,
        status: 'SUBMITTED',
      }));

      setShowSuccessModal(true);

      if (versionParam) {
        navigate(`/staff/price-lists/${id}`, { replace: true });
      } else {
        fetchDetail();
      }
    } catch (err) {
      alert(`Gửi phê duyệt thất bại:\n${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const renderStatusBadge = (status) => {
    switch (status) {
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
        return <span className="px-2.5 py-0.5 rounded bg-purple-100/80 text-purple-700 text-[10px] font-bold tracking-wide">SUPERSEDED</span>;
      case 'EXPIRED':
        return <span className="px-2.5 py-0.5 rounded bg-slate-200 text-slate-700 text-[10px] font-bold tracking-wide">EXPIRED</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-bold">{status}</span>;
    }
  };

  if (loading) {
    return (
      <div className="min-h-[400px] flex flex-col items-center justify-center space-y-3 text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin text-[#2b727d]" />
        <span className="text-xs font-medium">Đang tải chi tiết bảng giá từ server...</span>
      </div>
    );
  }

  if (error || !priceDetail) {
    return (
      <div className="bg-white p-8 rounded-xl border border-slate-200 text-center space-y-4 max-w-lg mx-auto mt-10 shadow-xs">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-800">Không thể tải thông tin</h2>
        <p className="text-xs text-slate-500">{error || 'Bảng giá không tồn tại.'}</p>
        <button
          onClick={() => navigate('/staff/price-lists')}
          className="px-4 py-2 bg-[#2b727d] text-white rounded-lg text-xs font-semibold hover:bg-[#235d67] transition cursor-pointer"
        >
          Quay lại danh sách
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5 text-slate-700 font-sans max-w-7xl mx-auto pb-10 relative">
      {/* HEADER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start space-x-4">
          <button
            onClick={() => navigate('/staff/price-lists')}
            className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 shadow-xs flex items-center space-x-1.5 cursor-pointer mt-0.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Quay lại</span>
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Xem chi tiết bảng giá</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Thông tin chi tiết cấu hình định mức đơn giá dịch vụ áp dụng.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Dropdown chọn nhanh phiên bản */}
          {versionsList.length > 0 && (
            <div className="flex items-center space-x-1.5">
              <Clock className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={priceDetail.version}
                onChange={handleVersionSelectChange}
                className="px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-slate-700 font-mono text-xs font-semibold focus:outline-none cursor-pointer hover:bg-slate-100 transition"
              >
                {versionsList.map((v) => {
                  const verStr = v.version || v.version_number || `v${v.version_number}`;
                  return (
                    <option key={v.id || v.version} value={verStr}>
                      Phiên bản: {verStr} ({v.status})
                    </option>
                  );
                })}
              </select>
            </div>
          )}

          {renderStatusBadge(priceDetail.status)}
        </div>
      </div>

      {/* REJECTED BANNER */}
      {priceDetail.status === 'REJECTED' && (
        <div className="bg-rose-50/80 border border-rose-200 text-rose-800 rounded-xl p-4 flex items-start space-x-3 shadow-xs">
          <AlertTriangle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <h4 className="font-bold text-rose-900 text-sm">Bảng giá này đã bị từ chối phê duyệt!</h4>
            <p className="text-[11px] text-rose-600">
              * Vui lòng chỉnh sửa lại các thông tin tương ứng bên dưới và nhấn <b className="text-rose-700">"Gửi phê duyệt"</b> lại.
            </p>
          </div>
        </div>
      )}

      {/* SUPERSEDED BANNER */}
      {priceDetail.status === 'SUPERSEDED' && (
        <div className="bg-purple-50/80 border border-purple-200 text-purple-900 rounded-xl p-4 flex items-start space-x-3 shadow-xs">
          <Archive className="w-5 h-5 text-purple-600 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <h4 className="font-bold text-purple-900 text-sm">Phiên bản đã bị thay thế (SUPERSEDED)</h4>
            <p className="text-[11px] text-purple-700">
              * Đây là phiên bản lưu trữ cũ. Một phiên bản mới hơn đã được phát hành và đang áp dụng. Bạn chỉ có thể xem dữ liệu lịch sử này.
            </p>
          </div>
        </div>
      )}

      {/* EXPIRED BANNER */}
      {priceDetail.status === 'EXPIRED' && (
        <div className="bg-slate-100 border border-slate-300 text-slate-800 rounded-xl p-4 flex items-start space-x-3 shadow-xs">
          <CalendarX className="w-5 h-5 text-slate-600 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <h4 className="font-bold text-slate-900 text-sm">Bảng giá đã hết hiệu lực (EXPIRED)</h4>
            <p className="text-[11px] text-slate-600">
              * Phiên bản này đã quá thời gian hiệu lực và không còn giá trị áp dụng trong hệ thống.
            </p>
          </div>
        </div>
      )}

      {/* MAIN FORM */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-7">
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
            <span className="text-[#2b727d]">|</span>
            <span>1. Thông tin chung bảng giá</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Mã bảng giá *</label>
              <input
                type="text"
                value={priceDetail.priceCode}
                readOnly
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 font-medium focus:outline-none cursor-default"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Tên bảng giá *</label>
              <input
                type="text"
                value={priceDetail.priceName}
                onChange={(e) => handleInputChange('priceName', e.target.value)}
                readOnly={!canEdit}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium transition-all focus:outline-none ${
                  canEdit
                    ? 'bg-white text-slate-800 focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10'
                    : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Loại đối tượng áp dụng *</label>
              {canEdit ? (
                <select
                  value={priceDetail.targetType}
                  onChange={(e) => handleInputChange('targetType', e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 font-medium bg-white text-slate-800 focus:outline-none focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10 transition-all cursor-pointer"
                >
                  <option value="CUSTOMER">CUSTOMER</option>
                  <option value="CONTRACT">CONTRACT</option>
                  <option value="GENERAL">GENERAL</option>
                </select>
              ) : (
                <input
                  type="text"
                  value={priceDetail.targetType}
                  readOnly
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 font-medium focus:outline-none cursor-default"
                />
              )}
            </div>

            {/* HIỂN THỊ ĐỐI TƯỢNG CỤ THỂ - Ô INPUT BÌNH THƯỜNG */}
            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Đối tượng áp dụng cụ thể *</label>
              {canEdit ? (
                priceDetail.targetType === 'GENERAL' ? (
                  <input
                    type="text"
                    disabled
                    value="Áp dụng cho tất cả (Chung)"
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-400 italic focus:outline-none cursor-default"
                  />
                ) : (
                  <select
                    value={priceDetail.specificTarget}
                    onChange={(e) => handleInputChange('specificTarget', e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-slate-200 font-medium bg-white text-slate-800 focus:outline-none focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10 transition-all cursor-pointer"
                  >
                    <option value="">
                      -- Chọn {priceDetail.targetType === 'CUSTOMER' ? 'Khách hàng' : 'Hợp đồng'} --
                    </option>
                    {targetOptions.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.code || opt.id}
                      </option>
                    ))}
                  </select>
                )
              ) : (
                <input
                  type="text"
                  value={
                    priceDetail.targetType === 'GENERAL'
                      ? 'Áp dụng chung (Tất cả đối tượng)'
                      : (selectedTargetObj?.code || priceDetail.specificTarget || '')
                  }
                  readOnly
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 font-medium focus:outline-none cursor-default"
                />
              )}
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực từ *</label>
              <input
                type="date"
                value={priceDetail.effectiveFrom}
                onChange={(e) => handleInputChange('effectiveFrom', e.target.value)}
                readOnly={!canEdit}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium transition-all focus:outline-none ${
                  canEdit
                    ? 'bg-white text-slate-800 focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10'
                    : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực đến *</label>
              <input
                type="date"
                value={priceDetail.effectiveTo}
                onChange={(e) => handleInputChange('effectiveTo', e.target.value)}
                readOnly={!canEdit}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium transition-all focus:outline-none ${
                  canEdit
                    ? 'bg-white text-slate-800 focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10'
                    : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>

            {priceDetail.status === 'REJECTED' && (
              <div className="md:col-span-3 pt-1">
                <label className="block text-rose-700 font-medium mb-1.5">Lý do từ chối từ Ban quản lý</label>
                <textarea
                  rows={2}
                  readOnly
                  value={priceDetail.rejectionReason || 'Chưa ghi nhận lý do cụ thể.'}
                  className="w-full px-3 py-2 rounded-lg border border-rose-200 bg-rose-50/50 text-rose-900 font-medium text-xs focus:outline-none cursor-default resize-none"
                />
              </div>
            )}
          </div>
        </div>

        {/* SERVICES LIST */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
              <span className="text-[#2b727d]">|</span>
              <span>2. Cấu hình đơn giá dịch vụ chi tiết</span>
            </h2>

            {canEdit && (
              <button
                onClick={handleAddService}
                type="button"
                className="px-3 py-1.5 rounded-lg border border-[#2b727d] text-[#2b727d] hover:bg-[#2b727d]/5 text-xs font-semibold flex items-center space-x-1 transition cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm dịch vụ</span>
              </button>
            )}
          </div>

          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold">
                  <th className="py-3 px-4 w-[35%]">Dịch vụ cung cấp</th>
                  <th className="py-3 px-4 w-[20%]">Mã dịch vụ</th>
                  <th className="py-3 px-4 w-[15%]">Đơn vị tính</th>
                  <th className="py-3 px-4 w-[20%] text-right">Đơn giá định mức</th>
                  {canEdit && <th className="py-3 px-4 w-[10%] text-center">Thao tác</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {priceDetail.services && priceDetail.services.length > 0 ? (
                  priceDetail.services.map((srv, index) => (
                    <tr key={index} className="hover:bg-slate-50/50 transition">
                      <td className="py-2.5 px-4">
                        {canEdit ? (
                          <select
                            value={srv.serviceCode}
                            onChange={(e) => handleSelectServiceChange(index, e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-[#2b727d] focus:ring-1 focus:ring-[#2b727d] bg-white text-slate-800"
                          >
                            <option value="">-- Chọn dịch vụ --</option>
                            {availableServices.map((s, idx) => {
                              const code = s.serviceCode || s.code;
                              const name = s.serviceName || s.name;
                              return (
                                <option key={idx} value={code}>
                                  {name} ({code})
                                </option>
                              );
                            })}
                          </select>
                        ) : (
                          <span className="text-slate-800 font-medium">{srv.serviceName}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4">
                        {canEdit ? (
                          <input
                            type="text"
                            value={srv.serviceCode}
                            readOnly
                            placeholder="Mã..."
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 font-mono bg-slate-50 text-slate-500 cursor-default"
                          />
                        ) : (
                          <span className="text-slate-500 font-mono">{srv.serviceCode}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4">
                        {canEdit ? (
                          <input
                            type="text"
                            value={srv.unit}
                            onChange={(e) => handleServiceChange(index, 'unit', e.target.value)}
                            placeholder="ĐVT..."
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-[#2b727d] focus:ring-1 focus:ring-[#2b727d]"
                          />
                        ) : (
                          <span className="text-slate-600">{srv.unit}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4 text-right">
                        {canEdit ? (
                          <div className="flex items-center justify-end space-x-2">
                            <input
                              type="text"
                              value={formatNumberWithDots(srv.price)}
                              onChange={(e) => handleServiceChange(index, 'price', e.target.value)}
                              className="w-28 px-3 py-1.5 rounded-lg border border-slate-200 text-right font-bold text-slate-800 focus:outline-none focus:border-[#2b727d] focus:ring-1 focus:ring-[#2b727d] transition-all"
                            />
                            <span className="text-xs font-medium text-slate-400 select-none">VND</span>
                          </div>
                        ) : (
                          <div className="flex items-center justify-end space-x-2">
                            <span className="font-bold text-slate-800 text-sm">
                              {formatNumberWithDots(srv.price)}
                            </span>
                            <span className="text-xs font-medium text-slate-400 select-none">VND</span>
                          </div>
                        )}
                      </td>
                      {canEdit && (
                        <td className="py-2.5 px-4 text-center">
                          <button
                            type="button"
                            onClick={() => handleRemoveServiceClick(index)}
                            className="p-1 text-slate-400 hover:text-rose-600 transition cursor-pointer"
                            title="Xóa dịch vụ"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      )}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={canEdit ? 5 : 4} className="py-8 text-center text-slate-400 text-xs">
                      Không tìm thấy danh sách dịch vụ chi tiết.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* ACTIONS BAR */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-end space-x-3">
        <button
          onClick={() => navigate(`/staff/price-lists/${id}/versions`)}
          className="px-4 py-2 rounded-lg border border-[#2b727d]/40 bg-[#f4fbf9] text-[#2b727d] hover:bg-[#e6f4f1] text-xs font-semibold flex items-center space-x-1.5 transition cursor-pointer shadow-xs"
        >
          <History className="w-3.5 h-3.5" />
          <span>Xem phiên bản khác</span>
        </button>

        <button
          onClick={() => navigate('/staff/price-lists')}
          className="px-5 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
        >
          Đóng
        </button>

        <button
          disabled={!canEdit || saving}
          onClick={handleSaveUpdate}
          className={`px-5 py-2 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
            canEdit
              ? 'bg-[#2b727d] hover:bg-[#235d67] text-white shadow-xs cursor-pointer'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed select-none'
          }`}
        >
          {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>Cập nhật</span>
        </button>

        <button
          disabled={!canEdit || submitting}
          onClick={handleSubmitApproval}
          className={`px-5 py-2 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
            canEdit
              ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs cursor-pointer'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed select-none'
          }`}
        >
          {submitting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Send className="w-3.5 h-3.5" />
          )}
          <span>Gửi phê duyệt</span>
        </button>
      </div>

      {/* MODAL XÁC NHẬN XÓA DỊCH VỤ */}
      {serviceToDeleteIndex !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in">
          <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-2xl text-center space-y-4 border border-slate-100">
            <div className="w-12 h-12 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center mx-auto">
              <Trash2 className="w-6 h-6" />
            </div>

            <div className="space-y-1.5">
              <h3 className="text-base font-bold text-slate-800">Xác nhận xóa dịch vụ</h3>
              <p className="text-xs text-slate-500 leading-relaxed">
                Bạn có chắc chắn muốn xóa dịch vụ này khỏi bảng giá không? Hành động này chưa thể hoàn tất cho đến khi bạn lưu bảng giá.
              </p>
            </div>

            <div className="pt-2 flex items-center space-x-3">
              <button
                onClick={() => setServiceToDeleteIndex(null)}
                className="w-1/2 py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg transition cursor-pointer"
              >
                Hủy
              </button>
              <button
                onClick={confirmRemoveService}
                className="w-1/2 py-2 px-3 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-lg transition shadow-xs cursor-pointer"
              >
                Xóa
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL UPDATE SUCCESS */}
      {showUpdateSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl text-center space-y-6 border border-slate-100">
            <div className="w-16 h-16 bg-[#e6f8ed] text-[#34a853] rounded-full flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 stroke-[3]" />
            </div>

            <div className="space-y-3">
              <h3 className="text-xl font-bold text-slate-900">Lưu thành công !</h3>
              <p className="text-sm text-slate-500 leading-relaxed px-4">
                Mọi thay đổi về định mức đơn giá và thời gian hiệu lực đã được cập nhật thành công.
              </p>
            </div>

            <div className="pt-2">
              <button
                onClick={() => setShowUpdateSuccessModal(false)}
                className="w-full py-3 px-4 bg-[#4d8b82] hover:bg-[#3f736c] text-white font-medium text-sm rounded-xl transition shadow-xs cursor-pointer"
              >
                Xác nhận
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL SUBMIT SUCCESS */}
      {showSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl text-center space-y-5 border border-slate-100">
            <div className="w-16 h-16 bg-emerald-100/80 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-9 h-9 stroke-[3]" />
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-slate-800">Gửi phê duyệt thành công!</h3>
              <p className="text-xs text-slate-500 leading-relaxed px-2">
                Phiên bản mới với trạng thái <span className="font-bold text-[#2b727d]">SUBMITTED</span> đã được tạo. Bạn có thể ra ngoài danh sách để kiểm tra.
              </p>
            </div>

            <div className="pt-2 flex items-center space-x-3">
              <button
                onClick={() => setShowSuccessModal(false)}
                className="w-1/2 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg transition cursor-pointer"
              >
                Ở lại trang này
              </button>
              <button
                onClick={() => navigate('/staff/price-lists')}
                className="w-1/2 py-2.5 px-3 bg-[#2b727d] hover:bg-[#235d67] text-white font-semibold text-xs rounded-lg transition shadow-xs cursor-pointer"
              >
                Xem danh sách ngoài
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}