import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Loader2, AlertCircle, Plus, Trash2, Send, Check, AlertTriangle } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8082/api/v1/price-lists';
const APPROVAL_BASE_URL = 'http://localhost:8082/api/v1/approvals';

export default function PriceListDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [priceDetail, setPriceDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [showUpdateSuccessModal, setShowUpdateSuccessModal] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

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

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    setError(null);

    fetch(`${API_BASE_URL}/${id}`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Không thể lấy thông tin chi tiết (Mã lỗi: ${res.status})`);
        }
        return res.json();
      })
      .then((data) => {
        setPriceDetail({
          priceCode: data.priceCode || data.id || id,
          priceName: data.priceName || '',
          targetType: data.targetType || data.scopeType || 'CUSTOMER',
          specificTarget: data.specificTarget || data.scopeId || '',
          effectiveFrom: data.effectiveFrom || data.validFrom || '',
          effectiveTo: data.effectiveTo || data.validTo || '',
          version: data.version || '1.0',
          status: (data.status || 'DRAFT').toUpperCase(),
          rejectionReason: data.rejectReason || data.rejectionReason || data.rejectionNote || '',
          services: (data.services || []).map((srv) => ({
            serviceCode: srv.serviceCode || srv.code || '',
            serviceName: srv.serviceName || srv.name || '',
            unit: srv.unit || '',
            price: srv.price || 0,
          })),
        });
        setLoading(false);
      })
      .catch((err) => {
        console.error('Lỗi API:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  const canEdit = priceDetail?.status === 'DRAFT' || priceDetail?.status === 'REJECTED';

  const handleInputChange = (field, value) => {
    setPriceDetail((prev) => ({
      ...prev,
      [field]: value,
    }));
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

  const handleRemoveService = (index) => {
    setPriceDetail((prev) => ({
      ...prev,
      services: prev.services.filter((_, i) => i !== index),
    }));
  };

  const handleSaveUpdate = async () => {
    setSaving(true);
    try {
      const payload = {
        price_code: priceDetail.priceCode,
        price_name: priceDetail.priceName,
        target_type: priceDetail.targetType,
        specific_target: priceDetail.specificTarget,
        effective_from: priceDetail.effectiveFrom,
        effective_to: priceDetail.effectiveTo,
        status: priceDetail.status,
        version: priceDetail.version,
        services: (priceDetail.services || []).map((s) => ({
          service_code: s.serviceCode || '',
          service_name: s.serviceName || '',
          unit: s.unit || '',
          price: Number(s.price) || 0,
        })),
      };

      const response = await fetch(`${API_BASE_URL}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
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
      const response = await fetch(`${APPROVAL_BASE_URL}/${priceDetail.priceCode}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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

      setPriceDetail((prev) => ({ ...prev, status: 'SUBMITTED' }));
      setShowSuccessModal(true);
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
      case 'EFFECTIVE':
      case 'APPROVED':
        return <span className="px-2.5 py-0.5 rounded bg-emerald-100/70 text-emerald-700 text-[10px] font-bold tracking-wide">EFFECTIVE</span>;
      case 'DRAFT':
        return <span className="px-2.5 py-0.5 rounded bg-amber-100/70 text-amber-700 text-[10px] font-bold tracking-wide">DRAFT</span>;
      case 'REJECTED':
        return <span className="px-2.5 py-0.5 rounded bg-rose-100/70 text-rose-700 text-[10px] font-bold tracking-wide">REJECTED</span>;
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

        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[10px] font-semibold">
            Phiên bản: {priceDetail.version}
          </span>
          {renderStatusBadge(priceDetail.status)}
        </div>
      </div>

      {priceDetail.status === 'REJECTED' && (
        <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-xl p-4 flex items-start space-x-3 shadow-xs animate-in fade-in">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <h4 className="font-bold text-rose-900 text-sm">Bảng giá này đã bị từ chối phê duyệt!</h4>
            <p className="text-[11px] text-rose-600 pt-0.5">
              * Vui lòng chỉnh sửa lại các thông tin tương ứng bên dưới và nhấn <b>"Gửi phê duyệt"</b> lại.
            </p>
          </div>
        </div>
      )}

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
                  <option value="CUSTOMER">Khách hàng (CUSTOMER)</option>
                  <option value="PARTNER">Đối tác (PARTNER)</option>
                  <option value="TIER">Hạng hội viên (TIER)</option>
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

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Đối tượng áp dụng cụ thể *</label>
              <input
                type="text"
                value={priceDetail.specificTarget}
                onChange={(e) => handleInputChange('specificTarget', e.target.value)}
                readOnly={!canEdit}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium transition-all focus:outline-none ${
                  canEdit
                    ? 'bg-white text-slate-800 focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10'
                    : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
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
              <div className="md:col-span-3">
                <label className="block text-rose-700 font-medium mb-1.5">Lý do từ chối từ Ban quản lý</label>
                <textarea
                  rows={2}
                  readOnly
                  value={priceDetail.rejectionReason || 'Chưa ghi nhận lý do từ chối cụ thể.'}
                  className="w-full px-3 py-2 rounded-lg border border-rose-200 bg-rose-50/50 text-rose-900 font-medium text-xs focus:outline-none cursor-default resize-none"
                />
              </div>
            )}
          </div>
        </div>

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
                          <input
                            type="text"
                            value={srv.serviceName}
                            placeholder="Tên dịch vụ..."
                            onChange={(e) => handleServiceChange(index, 'serviceName', e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-[#2b727d] focus:ring-1 focus:ring-[#2b727d]"
                          />
                        ) : (
                          <span className="text-slate-800 font-medium">{srv.serviceName}</span>
                        )}
                      </td>
                      <td className="py-2.5 px-4">
                        {canEdit ? (
                          <input
                            type="text"
                            value={srv.serviceCode}
                            placeholder="Mã..."
                            onChange={(e) => handleServiceChange(index, 'serviceCode', e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 font-mono focus:outline-none focus:border-[#2b727d] focus:ring-1 focus:ring-[#2b727d]"
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
                            placeholder="ĐVT..."
                            onChange={(e) => handleServiceChange(index, 'unit', e.target.value)}
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
                            onClick={() => handleRemoveService(index)}
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

      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-end space-x-3">
        <button
          onClick={() => navigate('/staff/price-lists')}
          className="px-5 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer"
        >
          Đóng
        </button>

        <button
          onClick={() => alert('Chức năng lịch sử phiên bản!')}
          className="px-4 py-2 rounded-lg bg-white border border-[#2b727d] text-[#2b727d] hover:bg-[#2b727d]/5 text-xs font-semibold flex items-center space-x-1.5 cursor-pointer transition"
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Xem phiên bản khác</span>
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

      {showUpdateSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl text-center space-y-6 border border-slate-100">
            <div className="w-16 h-16 bg-[#e6f8ed] text-[#34a853] rounded-full flex items-center justify-center mx-auto">
              <Check className="w-8 h-8 stroke-[3]" />
            </div>

            <div className="space-y-3">
              <h3 className="text-xl font-bold text-slate-900">
                Cập nhật thành công !
              </h3>
              <p className="text-sm text-slate-500 leading-relaxed px-4">
                Mọi thay đổi về định mức đơn giá và thời gian hiệu lực đã được lưu vào hệ thống
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

      {showSuccessModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs transition-opacity animate-in fade-in">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl text-center space-y-5 border border-slate-100">
            <div className="w-16 h-16 bg-emerald-100/80 text-emerald-600 rounded-full flex items-center justify-center mx-auto">
              <Check className="w-9 h-9 stroke-[3]" />
            </div>

            <div className="space-y-2">
              <h3 className="text-xl font-bold text-slate-800">
                Gửi phê duyệt thành công!
              </h3>
              <p className="text-xs text-slate-500 leading-relaxed px-2">
                Hệ thống đã gửi dữ liệu bảng giá <span className="font-bold text-slate-700">{priceDetail.priceCode}</span> đến ban điều hành xem xét duyệt bản ghi.
              </p>
            </div>

            <div className="pt-2">
              <button
                onClick={() => setShowSuccessModal(false)}
                className="w-full py-2.5 px-4 bg-[#2b727d] hover:bg-[#235d67] text-white font-semibold text-xs rounded-lg transition shadow-xs cursor-pointer"
              >
                Xác nhận
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}