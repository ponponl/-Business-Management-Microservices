import React, { useState, useEffect } from 'react';
import { ArrowLeft, Plus, Trash2, Check, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const BACKEND_BASE_URL = 'http://localhost:8082';

export default function CreatePriceListPage() {
  const navigate = useNavigate();

  // Lấy Token xác thực từ localStorage
  const token = localStorage.getItem('token');

  const [serviceOptions, setServiceOptions] = useState([]);
  const [isLoadingServices, setIsLoadingServices] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalConfig, setModalConfig] = useState({
    isOpen: false,
    type: '',
    title: '',
    message: '',
    btnText: 'Đóng'
  });

  const [formData, setFormData] = useState({
    priceCode: `PL-${new Date().getFullYear()}-${Math.floor(100 + Math.random() * 900)}`,
    priceName: '',
    targetType: 'CUSTOMER',
    specificTarget: '',
    effectiveFrom: new Date().toISOString().split('T')[0],
    effectiveTo: ''
  });

  const [services, setServices] = useState([]);

  const formatCurrency = (value) => {
    if (!value) return '0';
    const num = String(value).replace(/\D/g, '');
    return num ? new Intl.NumberFormat('vi-VN').format(Number(num)) : '0';
  };

  const parseCurrency = (value) =>
    parseFloat(String(value).replace(/\./g, '').replace(/,/g, '')) || 0;

  useEffect(() => {
    const initDefaultRow = () => {
      setServices([{
        id: Date.now(),
        serviceName: '',
        serviceCode: `SRV-${Date.now().toString().slice(-4)}`,
        unit: 'Lượt',
        price: '0'
      }]);
    };

    const fetchServices = async () => {
      try {
        const response = await fetch(`${BACKEND_BASE_URL}/api/v1/services`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          initDefaultRow();
          return;
        }

        const data = await response.json();
        setServiceOptions(Array.isArray(data) ? data : []);

        if (data?.length > 0) {
          const first = data[0];
          setServices([{
            id: Date.now(),
            serviceName: first.service_name || first.name || '',
            serviceCode: first.service_code || first.code || '',
            unit: first.unit || 'Lượt',
            price: '0'
          }]);
        } else {
          initDefaultRow();
        }
      } catch (error) {
        console.warn('Không kết nối được API dịch vụ:', error);
        initDefaultRow();
      } finally {
        setIsLoadingServices(false);
      }
    };

    fetchServices();
  }, [token]);

  const handleAddRow = () => {
    const defaultSrv = serviceOptions[0];

    setServices((prev) => [...prev, {
      id: Date.now(),
      serviceName: defaultSrv?.service_name || defaultSrv?.name || '',
      serviceCode: defaultSrv?.service_code || defaultSrv?.code || `SRV-${Date.now().toString().slice(-4)}`,
      unit: defaultSrv?.unit || 'Lượt',
      price: '0'
    }]);
  };

  const handleRemoveRow = (id) => {
    if (services.length === 1) return;
    setServices((prev) => prev.filter((srv) => srv.id !== id));
  };

  const handleServiceChange = (id, field, value) => {
    setServices((prev) => prev.map((srv) => {
      if (srv.id !== id) return srv;

      if (field === 'serviceName') {
        const selected = serviceOptions.find(
          (item) => (item.service_name || item.name) === value
        );

        return {
          ...srv,
          serviceName: value,
          serviceCode: selected?.service_code || selected?.code || srv.serviceCode,
          unit: selected?.unit || srv.unit
        };
      }

      if (field === 'price') {
        return { ...srv, price: formatCurrency(value) };
      }

      return { ...srv, [field]: value };
    }));
  };

  const preparePayload = (statusType) => ({
    priceCode: formData.priceCode.trim(),
    price_code: formData.priceCode.trim(),
    priceName: formData.priceName.trim(),
    price_name: formData.priceName.trim(),
    targetType: formData.targetType,
    target_type: formData.targetType,
    specificTarget: formData.specificTarget,
    specific_target: formData.specificTarget,
    effectiveFrom: formData.effectiveFrom,
    effective_from: formData.effectiveFrom,
    effectiveTo: formData.effectiveTo || null,
    effective_to: formData.effectiveTo || null,
    status: statusType,
    version: '1.0',
    services: services.map((s) => ({
      serviceCode: s.serviceCode,
      service_code: s.serviceCode,
      serviceName: s.serviceName,
      service_name: s.serviceName,
      unit: s.unit,
      price: parseCurrency(s.price)
    }))
  });

  const submitDataToApi = async (statusType) => {
    if (!formData.priceName.trim()) {
      alert('Vui lòng nhập Tên bảng giá!');
      return;
    }

    if (!formData.effectiveTo) {
      alert('Vui lòng chọn Thời gian hiệu lực đến!');
      return;
    }

    if (new Date(formData.effectiveTo) <= new Date(formData.effectiveFrom)) {
      alert('Thời gian hiệu lực đến phải lớn hơn thời gian bắt đầu!');
      return;
    }

    if (services.length === 0) {
      alert('Bảng giá phải có ít nhất 1 dịch vụ!');
      return;
    }

    const hasInvalidService = services.some(
      (s) => !s.serviceName.trim() || parseCurrency(s.price) <= 0
    );

    if (hasInvalidService) {
      alert('Vui lòng chọn tên dịch vụ và nhập đơn giá lớn hơn 0 cho tất cả các dòng!');
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${BACKEND_BASE_URL}/api/v1/price-lists`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(preparePayload(statusType))
      });

      const responseText = await response.text();
      let responseData = {};

      try {
        responseData = responseText ? JSON.parse(responseText) : {};
      } catch {
        console.warn('Response từ backend không phải JSON:', responseText);
      }

      if (!response.ok) {
        throw new Error(
          responseData.detail ||
          responseData.message ||
          responseText ||
          `Yêu cầu thất bại (Mã lỗi ${response.status})`
        );
      }

      const targetCode =
        responseData.priceCode ||
        responseData.price_code ||
        responseData.price_list_code ||
        responseData.code ||
        formData.priceCode;

      setModalConfig({
        isOpen: true,
        type: statusType === 'DRAFT' ? 'draft' : 'submit',
        title: statusType === 'DRAFT'
          ? 'Đã lưu bản ghi nháp!'
          : 'Gửi phê duyệt thành công!',
        message: statusType === 'DRAFT'
          ? `Dữ liệu bảng giá ${targetCode} đã lưu thành công ở trạng thái nháp (Draft).`
          : `Bảng giá ${targetCode} đã được tạo ở trạng thái SUBMITTED và chuyển đến cấp Quản lý phê duyệt.`,
        btnText: statusType === 'DRAFT' ? 'Đóng' : 'Xác nhận'
      });
    } catch (error) {
      console.error('Lỗi khi tạo bảng giá:', error);
      alert(`Thất bại: ${error.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmModal = () => {
    setModalConfig((prev) => ({ ...prev, isOpen: false }));
    navigate('/staff/price-lists');
  };

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
                onChange={(e) => setFormData({ ...formData, priceName: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Loại đối tượng áp dụng *</label>
              <select
                value={formData.targetType}
                onChange={(e) => setFormData({ ...formData, targetType: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white cursor-pointer font-medium text-slate-700"
              >
                <option value="CUSTOMER">Khách hàng (CUSTOMER)</option>
                <option value="CONTRACT">Hợp đồng (CONTRACT)</option>
                <option value="GENERAL">Chung (GENERAL)</option>
              </select>
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Đối tượng áp dụng cụ thể</label>
              <input
                type="text"
                placeholder="Nhập mã khách hàng hoặc mã hợp đồng..."
                value={formData.specificTarget}
                onChange={(e) => setFormData({ ...formData, specificTarget: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực từ *</label>
              <input
                type="date"
                value={formData.effectiveFrom}
                onChange={(e) => setFormData({ ...formData, effectiveFrom: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white text-slate-700"
              />
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">Thời gian hiệu lực đến *</label>
              <input
                type="date"
                value={formData.effectiveTo}
                onChange={(e) => setFormData({ ...formData, effectiveTo: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white text-slate-700"
              />
            </div>
          </div>
        </div>

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
                {isLoadingServices ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-400 font-medium">
                      <div className="flex justify-center items-center space-x-2">
                        <Loader2 className="w-4 h-4 animate-spin text-[#2b727d]" />
                        <span>Đang tải danh sách dịch vụ...</span>
                      </div>
                    </td>
                  </tr>
                ) : services.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-slate-400 font-medium">
                      Chưa có dịch vụ nào. Hãy bấm "Thêm dòng dịch vụ".
                    </td>
                  </tr>
                ) : (
                  services.map((service) => (
                    <tr key={service.id} className="hover:bg-slate-50/50 transition">
                      <td className="py-2.5 px-4">
                        {serviceOptions.length > 0 ? (
                          <select
                            value={service.serviceName}
                            onChange={(e) => handleServiceChange(service.id, 'serviceName', e.target.value)}
                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white font-medium text-slate-800 cursor-pointer"
                          >
                            <option value="" disabled>-- Chọn dịch vụ --</option>
                            {serviceOptions.map((opt, idx) => {
                              const optName = opt.service_name || opt.name;
                              const optCode = opt.service_code || opt.code || idx;

                              return (
                                <option key={optCode} value={optName}>
                                  {optName}
                                </option>
                              );
                            })}
                          </select>
                        ) : (
                          <input
                            type="text"
                            placeholder="Nhập tên dịch vụ..."
                            value={service.serviceName}
                            onChange={(e) => handleServiceChange(service.id, 'serviceName', e.target.value)}
                            className="w-full px-3 py-1.5 rounded-lg border border-slate-200 focus:outline-none focus:border-sky-500 bg-white font-medium text-slate-800"
                          />
                        )}
                      </td>

                      <td className="py-2.5 px-4 text-slate-500 font-mono font-medium">
                        <input
                          type="text"
                          value={service.serviceCode}
                          onChange={(e) => handleServiceChange(service.id, 'serviceCode', e.target.value)}
                          className="w-full bg-transparent border-b border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white focus:outline-none font-mono"
                        />
                      </td>

                      <td className="py-2.5 px-4 text-slate-600">
                        <input
                          type="text"
                          value={service.unit}
                          onChange={(e) => handleServiceChange(service.id, 'unit', e.target.value)}
                          className="w-full bg-transparent border-b border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white focus:outline-none"
                        />
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
                          disabled={services.length === 1}
                          className="p-1 text-slate-400 hover:text-rose-600 transition cursor-pointer disabled:opacity-30"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-end space-x-3">
        <button
          onClick={() => navigate('/staff/price-lists')}
          disabled={isSubmitting}
          className="px-4 py-2 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 cursor-pointer disabled:opacity-50"
        >
          Hủy bỏ
        </button>

        <button
          onClick={() => submitDataToApi('DRAFT')}
          disabled={isSubmitting}
          className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-xs font-semibold text-slate-700 cursor-pointer transition flex items-center space-x-1.5 disabled:opacity-50"
        >
          {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>Lưu nháp</span>
        </button>

        <button
          onClick={() => submitDataToApi('SUBMITTED')}
          disabled={isSubmitting}
          className="px-5 py-2 rounded-lg bg-[#2b727d] hover:bg-[#235d67] text-xs font-semibold text-white shadow-xs transition cursor-pointer flex items-center space-x-1.5 disabled:opacity-50"
        >
          {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>Gửi phê duyệt</span>
        </button>
      </div>

      {modalConfig.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-[2px] p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-md w-full p-6 text-center space-y-4">
            <div className="flex justify-center">
              <div className={`w-14 h-14 rounded-full flex items-center justify-center ${
                modalConfig.type === 'draft'
                  ? 'bg-sky-100/70 text-sky-500'
                  : 'bg-emerald-100/70 text-emerald-500'
              }`}>
                <Check className="w-8 h-8 stroke-[2.5]" />
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-base font-bold text-slate-900">{modalConfig.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed px-2">{modalConfig.message}</p>
            </div>

            <button
              onClick={handleConfirmModal}
              className={`w-full py-2.5 px-4 rounded-lg text-xs font-semibold text-white shadow-xs transition cursor-pointer ${
                modalConfig.type === 'draft'
                  ? 'bg-sky-600 hover:bg-sky-700'
                  : 'bg-[#4b8882] hover:bg-[#3f756f]'
              }`}
            >
              {modalConfig.btnText}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}