import React, { useState } from 'react';
import { ArrowLeft, Plus, Trash2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Danh mục các dịch vụ sẵn có trong hệ thống
const SERVICE_OPTIONS = [
  { name: 'Bốc xếp container 20ft (Hàng nhập)', code: 'SRV-20ft-IN', unit: 'Container' },
  { name: 'Lưu kho bãi tổng hợp', code: 'SRV-WH-GEN', unit: 'Ngày/Tấn' },
  { name: 'Khai thác bến bãi hạ tải', code: 'SRV-PORT-OP', unit: 'Lượt xe' },
  { name: 'Bốc xếp container 40ft (Hàng xuất)', code: 'SRV-40ft-OUT', unit: 'Container' },
  { name: 'Khai báo hải quan trọn gói', code: 'SRV-CUST-CLR', unit: 'Tờ khai' },
];

export default function CreatePriceListPage() {
  const navigate = useNavigate();

  // 1. STATE QUẢN LÝ THÔNG TIN CHUNG
  const [formData, setFormData] = useState({
    priceCode: 'PL-2026-012',
    priceName: '',
    targetType: 'Khách hàng (CUSTOMER)',
    specificTarget: '',
    effectiveFrom: '2026-07-20',
    effectiveTo: '2027-07-20'
  });

  // 2. STATE QUẢN LÝ DANH SÁCH DỊCH VỤ CHI TIẾT
  const [services, setServices] = useState([
    {
      id: 1,
      serviceName: 'Bốc xếp container 20ft (Hàng nhập)',
      serviceCode: 'SRV-20ft-IN',
      unit: 'Container',
      price: '350.000'
    },
    {
      id: 2,
      serviceName: 'Lưu kho bãi tổng hợp',
      serviceCode: 'SRV-WH-GEN',
      unit: 'Ngày/Tấn',
      price: '45.000'
    },
    {
      id: 3,
      serviceName: 'Khai thác bến bãi hạ tải',
      serviceCode: 'SRV-PORT-OP',
      unit: 'Lượt xe',
      price: '120.000'
    },
    {
      id: 4,
      serviceName: 'Bốc xếp container 40ft (Hàng xuất)',
      serviceCode: 'SRV-40ft-OUT',
      unit: 'Container',
      price: '550.000'
    },
    {
      id: 5,
      serviceName: 'Khai báo hải quan trọn gói',
      serviceCode: 'SRV-CUST-CLR',
      unit: 'Tờ khai',
      price: '800.000'
    }
  ]);

  // Thêm một dòng dịch vụ mới (mặc định lấy dịch vụ đầu tiên)
  const handleAddRow = () => {
    const defaultSrv = SERVICE_OPTIONS[0];
    const newService = {
      id: Date.now(),
      serviceName: defaultSrv.name,
      serviceCode: defaultSrv.code,
      unit: defaultSrv.unit,
      price: '0'
    };
    setServices([...services, newService]);
  };

  // Xóa dòng dịch vụ
  const handleRemoveRow = (id) => {
    if (services.length === 1) return; // Giữ lại ít nhất 1 dòng
    setServices(services.filter(srv => srv.id !== id));
  };

  // Thay đổi thông tin dòng dịch vụ (Tự động map mã & ĐVT khi chọn tên dịch vụ)
  const handleServiceChange = (id, field, value) => {
    setServices(services.map(srv => {
      if (srv.id === id) {
        if (field === 'serviceName') {
          const selected = SERVICE_OPTIONS.find(item => item.name === value);
          return {
            ...srv,
            serviceName: value,
            serviceCode: selected ? selected.code : 'SRV-NEW',
            unit: selected ? selected.unit : 'Lượt'
          };
        }
        return { ...srv, [field]: value };
      }
      return srv;
    }));
  };

  return (
    <div className="space-y-5 text-slate-700 font-sans max-w-7xl mx-auto pb-10">
      
      {/* HEADER TẠO BẢNG GIÁ MỚI */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start space-x-4">
          {/* NÚT QUAY LẠI */}
          <button 
            onClick={() => navigate('/price-lists')}
            className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 shadow-xs flex items-center space-x-1.5 cursor-pointer mt-0.5"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Quay lại</span>
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Tạo bảng giá mới</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              Thiết lập thông tin cấu hình bảng giá và định mức đơn giá dịch vụ áp dụng.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <span className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-md border border-slate-200">
            Phiên bản: 1.0
          </span>
          <span className="px-3 py-1 bg-sky-50 text-sky-700 text-xs font-semibold rounded-md border border-sky-100">
            Trạng thái: DRAFT
          </span>
        </div>
      </div>

      {/* KHU VỰC THÔNG TIN VÀ CẤU HÌNH BẢNG GIÁ */}
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
                value={formData.priceCode}
                disabled
                className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-slate-50 text-slate-700 font-semibold focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Tên bảng giá *</label>
              <input 
                type="text" 
                placeholder="Nhập tên bảng giá chi tiết..."
                value={formData.priceName}
                onChange={(e) => setFormData({...formData, priceName: e.target.value})}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Loại đối tượng áp dụng *</label>
              <select 
                value={formData.targetType}
                onChange={(e) => setFormData({...formData, targetType: e.target.value})}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white cursor-pointer font-medium text-slate-700"
              >
                <option value="Khách hàng (CUSTOMER)">Khách hàng (CUSTOMER)</option>
                <option value="Hợp đồng (CONTRACT)">Hợp đồng (CONTRACT)</option>
                <option value="Chung (GENERAL)">Chung (GENERAL)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Đối tượng áp dụng cụ thể *</label>
              <input 
                type="text" 
                placeholder="Nhập mã khách hàng hoặc mã hợp đồng áp dụng..."
                value={formData.specificTarget}
                onChange={(e) => setFormData({...formData, specificTarget: e.target.value})}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực từ *</label>
              <input 
                type="date" 
                value={formData.effectiveFrom}
                onChange={(e) => setFormData({...formData, effectiveFrom: e.target.value})}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white text-slate-700"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực đến *</label>
              <input 
                type="date" 
                value={formData.effectiveTo}
                onChange={(e) => setFormData({...formData, effectiveTo: e.target.value})}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white text-slate-700"
              />
            </div>
          </div>
        </div>

        {/* 2. CẤU HÌNH ĐƠN GIÁ DỊCH VỤ CHI TIẾT */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-800 flex items-center space-x-2">
              <span className="text-[#2b727d]">|</span>
              <span>2. Cấu hình đơn giá dịch vụ chi tiết</span>
            </h2>
            <button 
              onClick={handleAddRow}
              className="px-3 py-1.5 rounded-lg border border-[#2b727d] text-[#2b727d] hover:bg-[#2b727d]/5 text-xs font-semibold flex items-center space-x-1 transition cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Thêm dòng dịch vụ</span>
            </button>
          </div>

          <div className="border border-slate-200 rounded-lg overflow-hidden">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold">
                  <th className="py-2.5 px-4 w-[35%]">Dịch vụ cung cấp *</th>
                  <th className="py-2.5 px-4 w-[18%]">Mã dịch vụ</th>
                  <th className="py-2.5 px-4 w-[15%]">Đơn vị tính</th>
                  <th className="py-2.5 px-4 w-[25%] text-right">Đơn giá định mức *</th>
                  <th className="py-2.5 px-4 w-[7%] text-center">Xóa</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {services.map((service) => (
                  <tr key={service.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-2.5 px-4">
                      <select 
                        value={service.serviceName}
                        onChange={(e) => handleServiceChange(service.id, 'serviceName', e.target.value)}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white font-medium text-slate-800 cursor-pointer"
                      >
                        {SERVICE_OPTIONS.map((opt) => (
                          <option key={opt.code} value={opt.name}>{opt.name}</option>
                        ))}
                      </select>
                    </td>

                    <td className="py-2.5 px-4 text-slate-500 font-mono font-medium">
                      {service.serviceCode}
                    </td>

                    <td className="py-2.5 px-4 text-slate-600">
                      {service.unit}
                    </td>

                    <td className="py-2.5 px-4">
                      <div className="flex items-center justify-end space-x-1.5">
                        <input 
                          type="text" 
                          value={service.price}
                          onChange={(e) => handleServiceChange(service.id, 'price', e.target.value)}
                          className="w-36 px-3 py-1.5 rounded-lg border border-slate-200 text-right font-bold text-slate-800 focus:outline-none focus:border-sky-500 bg-white"
                        />
                        <span className="text-[11px] font-semibold text-slate-400">VND</span>
                      </div>
                    </td>

                    <td className="py-2.5 px-4 text-center">
                      <button 
                        onClick={() => handleRemoveRow(service.id)}
                        className="p-1 text-slate-400 hover:text-rose-600 transition cursor-pointer"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
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
        {/* NÚT HỦY BỎ */}
        <button 
          onClick={() => navigate('/price-lists')}
          className="px-4 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer"
        >
          Hủy bỏ
        </button>
        <button 
          onClick={() => alert('Đã lưu nháp bảng giá!')}
          className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 cursor-pointer"
        >
          Lưu nháp
        </button>
        {/* NÚT GỬI PHÊ DUYỆT*/}
        <button 
          onClick={() => {
            alert('Đã gửi phê duyệt thành công!');
            navigate('/price-lists');
          }}
          className="px-5 py-2 rounded-lg bg-[#2b727d] hover:bg-[#235d67] text-xs font-semibold text-white shadow-xs transition cursor-pointer"
        >
          Gửi phê duyệt
        </button>
      </div>

    </div>
  );
}