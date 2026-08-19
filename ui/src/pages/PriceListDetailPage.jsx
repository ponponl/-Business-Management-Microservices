import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Clock, Loader2, AlertCircle } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8082/api/v1/price-lists';

export default function PriceListDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [priceDetail, setPriceDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

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
          targetType: data.targetType || data.scopeType || 'Khách hàng (CUSTOMER)',
          specificTarget: data.specificTarget || data.scopeId || '',
          effectiveFrom: data.effectiveFrom || data.validFrom || '',
          effectiveTo: data.effectiveTo || data.validTo || '',
          version: data.version || '1.0',
          status: data.status || 'DRAFT',
          services: data.services || []
        });
        setLoading(false);
      })
      .catch((err) => {
        console.error('Lỗi API:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [id]);

  const handleInputChange = (field, value) => {
    setPriceDetail((prev) => ({
      ...prev,
      [field]: value
    }));
  };

  const handleSaveUpdate = async () => {
    setSaving(true);
    try {
      const response = await fetch(`${API_BASE_URL}/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(priceDetail),
      });

      if (!response.ok) {
        throw new Error('Lỗi khi gửi yêu cầu cập nhật lên server!');
      }

      alert('Cập nhật bảng giá thành công!');
    } catch (err) {
      alert(`Cập nhật thất bại: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const isDraft = priceDetail?.status === 'DRAFT';

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
          onClick={() => navigate(-1)}
          className="px-4 py-2 bg-[#2b727d] text-white rounded-lg text-xs font-semibold hover:bg-[#235d67] transition cursor-pointer"
        >
          Quay lại
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5 text-slate-700 font-sans max-w-7xl mx-auto pb-10">
      
      {/* HEADER CHI TIẾT BẢNG GIÁ */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start space-x-4">
          <button 
            onClick={() => navigate(-1)}
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

      {/* KHU VỰC THÔNG TIN VÀ BẢNG GIÁ DỊCH VỤ */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-7">
        
        {/* 1. THÔNG TIN CHUNG BẢNG GIÁ */}
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
                readOnly={!isDraft}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium focus:outline-none ${
                  isDraft ? 'bg-white text-slate-800 focus:border-sky-500' : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Loại đối tượng áp dụng *</label>
              <div className="relative">
                <input 
                  type="text" 
                  value={priceDetail.targetType}
                  readOnly
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 font-medium focus:outline-none cursor-default"
                />
                <span className="absolute right-3 top-2.5 text-slate-400 text-xs">▼</span>
              </div>
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Đối tượng áp dụng cụ thể *</label>
              <input 
                type="text" 
                value={priceDetail.specificTarget}
                readOnly
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-800 font-medium focus:outline-none cursor-default"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực từ *</label>
              <input 
                type="date" 
                value={priceDetail.effectiveFrom}
                onChange={(e) => handleInputChange('effectiveFrom', e.target.value)}
                readOnly={!isDraft}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium focus:outline-none ${
                  isDraft ? 'bg-white text-slate-800 focus:border-sky-500' : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực đến *</label>
              <input 
                type="date" 
                value={priceDetail.effectiveTo}
                onChange={(e) => handleInputChange('effectiveTo', e.target.value)}
                readOnly={!isDraft}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium focus:outline-none ${
                  isDraft ? 'bg-white text-slate-800 focus:border-sky-500' : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>
          </div>
        </div>

        {/* 2. CẤU HÌNH ĐƠN GIÁ DỊCH VỤ CHI TIẾT */}
        <div className="space-y-4 pt-2">
          <h2 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
            <span className="text-[#2b727d]">|</span>
            <span>2. Cấu hình đơn giá dịch vụ chi tiết</span>
          </h2>

          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold">
                  <th className="py-3 px-4 w-[40%]">Dịch vụ cung cấp</th>
                  <th className="py-3 px-4 w-[20%]">Mã dịch vụ</th>
                  <th className="py-3 px-4 w-[20%]">Đơn vị tính</th>
                  <th className="py-3 px-4 w-[20%] text-right">Đơn giá định mức</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {priceDetail.services && priceDetail.services.length > 0 ? (
                  priceDetail.services.map((srv, index) => (
                    <tr key={srv.id || srv.code || index} className="hover:bg-slate-50/50 transition">
                      <td className="py-3 px-4 text-slate-800 font-medium">
                        {srv.name || srv.serviceName}
                      </td>
                      <td className="py-3 px-4 text-slate-500 font-mono">
                        {srv.code || srv.serviceCode}
                      </td>
                      <td className="py-3 px-4 text-slate-600">
                        {srv.unit}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="font-bold text-slate-800 mr-1.5">
                          {Number(srv.price || srv.unitPrice || 0).toLocaleString('vi-VN')}
                        </span>
                        <span className="text-[11px] text-slate-400 font-medium">VND</span>
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

      {/* BOTTOM BUTTON ACTION BAR */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-end space-x-3">
        <button 
          onClick={() => navigate(-1)}
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
          disabled={!isDraft || saving}
          onClick={handleSaveUpdate}
          className={`px-5 py-2 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition ${
            isDraft 
              ? 'bg-[#2b727d] hover:bg-[#235d67] text-white shadow-xs cursor-pointer' 
              : 'bg-slate-200 text-slate-400 cursor-not-allowed select-none'
          }`}
        >
          {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>Cập nhật</span>
        </button>
      </div>

    </div>
  );
}