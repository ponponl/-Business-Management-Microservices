import React, { useState } from 'react';
import { ArrowLeft, Clock } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function PriceListDetailPage() {
  const navigate = useNavigate();

  // Dữ liệu chi tiết bảng giá (mặc định trạng thái DRAFT)
  const [priceDetail, setPriceDetail] = useState({
    priceCode: 'PL-2026-012',
    priceName: 'Bảng giá bốc xếp hạ tải nội địa 2026',
    targetType: 'Khách hàng (CUSTOMER)',
    specificTarget: 'KH-LOGISTIC-TÂNPHÁT',
    effectiveFrom: '2026-07-20',
    effectiveTo: '2027-07-20',
    version: '1.0',
    status: 'DRAFT', // 'DRAFT' | 'SUBMITTED' | 'EFFECTIVE' | 'REJECTED'
    services: [
      { id: 1, name: 'Bốc xếp container 20ft (Hàng nhập)', code: 'SRV-20ft-IN', unit: 'Container', price: '350.000' },
      { id: 2, name: 'Lưu kho bãi tổng hợp', code: 'SRV-WH-GEN', unit: 'Ngày/Tấn', price: '45.000' },
      { id: 3, name: 'Khai thác bến bãi hạ tải', code: 'SRV-PORT-OP', unit: 'Lượt xe', price: '120.000' },
      { id: 4, name: 'Bốc xếp container 40ft (Hàng xuất)', code: 'SRV-40ft-OUT', unit: 'Container', price: '550.000' },
      { id: 5, name: 'Khai báo hải quan trọn gói', code: 'SRV-CUST-CLR', unit: 'Tờ khai', price: '800.000' },
    ]
  });

  const isDraft = priceDetail.status === 'DRAFT';

  const renderStatusBadge = (status) => {
    switch (status) {
      case 'DRAFT':
        return (
          <span className="px-3 py-1 bg-sky-50 text-sky-600 text-xs font-semibold rounded-md border border-sky-200">
            Trạng thái: DRAFT
          </span>
        );
      case 'SUBMITTED':
        return (
          <span className="px-3 py-1 bg-amber-50 text-amber-700 text-xs font-semibold rounded-md border border-amber-200/60">
            Trạng thái: SUBMITTED
          </span>
        );
      case 'EFFECTIVE':
        return (
          <span className="px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-md border border-emerald-200">
            Trạng thái: EFFECTIVE
          </span>
        );
      case 'REJECTED':
        return (
          <span className="px-3 py-1 bg-rose-50 text-rose-700 text-xs font-semibold rounded-md border border-rose-200">
            Trạng thái: REJECTED
          </span>
        );
      default:
        return null;
    }
  };

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
          <span className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-md border border-slate-200">
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
                type="text" 
                value={priceDetail.effectiveFrom}
                readOnly={!isDraft}
                className={`w-full px-3 py-2 rounded-lg border border-slate-200 font-medium focus:outline-none ${
                  isDraft ? 'bg-white text-slate-800 focus:border-sky-500' : 'bg-slate-50 text-slate-800 cursor-default'
                }`}
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực đến *</label>
              <input 
                type="text" 
                value={priceDetail.effectiveTo}
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
                {priceDetail.services.map((srv) => (
                  <tr key={srv.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-3 px-4 text-slate-800 font-medium">
                      {srv.name}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono">
                      {srv.code}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {srv.unit}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <span className="font-bold text-slate-800 mr-1.5">{srv.price}</span>
                      <span className="text-[11px] text-slate-400 font-medium">VND</span>
                    </td>
                  </tr>
                ))}
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

        {/* NÚT CẬP NHẬT: KHI Ở DRAFT SẼ KÍCH HOẠT MÀU XANH #2b727d */}
        <button 
          disabled={!isDraft}
          onClick={() => alert('Cập nhật bảng giá thành công!')}
          className={`px-5 py-2 rounded-lg text-xs font-semibold transition ${
            isDraft 
              ? 'bg-[#2b727d] hover:bg-[#235d67] text-white shadow-xs cursor-pointer' 
              : 'bg-slate-200 text-slate-400 cursor-not-allowed select-none'
          }`}
        >
          Cập nhật
        </button>
      </div>

    </div>
  );
}