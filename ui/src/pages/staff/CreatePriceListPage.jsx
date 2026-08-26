import React, { useState, useEffect } from 'react';
import { ArrowLeft, Plus, Trash2, Check, Loader2, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const BACKEND_BASE_URL = 'http://localhost:8082';

export default function CreatePriceListPage() {
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  const [serviceOptions, setServiceOptions] = useState([]);
  const [isLoadingServices, setIsLoadingServices] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

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
    effectiveTo: '',
    version: '1.0'
  });

  const [services, setServices] = useState([]);

  // Hàm ép kiểu và lấy giá trị đơn giá chuẩn từ đối tượng Dịch Vụ
  const extractPrice = (item) => {
    if (!item) return 0;
    const rawPrice = item.price ?? item.unit_price ?? item.unitPrice ?? item.standardPrice ?? item.base_price ?? 0;
    return parseFloat(rawPrice) || 0;
  };

  const formatCurrency = (value) => {
    if (value === undefined || value === null || value === '') return '0';
    const num = String(value).replace(/\D/g, '');
    return num ? new Intl.NumberFormat('vi-VN').format(Number(num)) : '0';
  };

  const parseCurrency = (value) =>
    parseFloat(String(value).replace(/\./g, '').replace(/,/g, '')) || 0;

  // Khởi tạo dòng mặc định linh hoạt
  const createRowFromOption = (opt) => {
    const sId = opt?.id || opt?.service_item_id || opt?.serviceItemId || null;
    const sName = opt?.service_name || opt?.serviceName || opt?.name || opt?.title || '';
    const sCode = opt?.service_code || opt?.serviceCode || opt?.code || '';
    const sGroup = opt?.service_group || opt?.serviceGroup || opt?.group || '';
    const sUnit = opt?.unit || 'Lượt';
    const sPrice = formatCurrency(extractPrice(opt));

    return {
      id: Date.now() + Math.random(),
      serviceItemId: sId,
      serviceName: sName,
      serviceCode: sCode,
      serviceGroup: sGroup,
      unit: sUnit,
      price: sPrice
    };
  };

  useEffect(() => {
    const initDefaultRow = () => {
      setServices([{
        id: Date.now(),
        serviceItemId: null,
        serviceName: '',
        serviceCode: '',
        serviceGroup: '',
        unit: 'Lượt',
        price: '0'
      }]);
    };

    const fetchServices = async () => {
      try {
        setIsLoadingServices(true);
        const response = await fetch(`${BACKEND_BASE_URL}/api/v1/price-lists/services`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          console.error('Lỗi khi gọi API dịch vụ:', await response.text());
          initDefaultRow();
          return;
        }

        const resData = await response.json();
        let list = [];
        if (Array.isArray(resData)) list = resData;
        else if (Array.isArray(resData?.data)) list = resData.data;
        else if (Array.isArray(resData?.content)) list = resData.content;
        else if (Array.isArray(resData?.items)) list = resData.items;

        setServiceOptions(list);

        if (list.length > 0) {
          setServices([createRowFromOption(list[0])]);
        } else {
          initDefaultRow();
        }
      } catch (error) {
        console.error('Lỗi ngoại lệ khi tải danh sách dịch vụ:', error);
        initDefaultRow();
      } finally {
        setIsLoadingServices(false);
      }
    };

    fetchServices();
  }, [token]);

  const handleAddRow = () => {
    const defaultSrv = serviceOptions[0];
    if (defaultSrv) {
      setServices((prev) => [...prev, createRowFromOption(defaultSrv)]);
    } else {
      setServices((prev) => [...prev, {
        id: Date.now(),
        serviceItemId: null,
        serviceName: '',
        serviceCode: '',
        serviceGroup: '',
        unit: 'Lượt',
        price: '0'
      }]);
    }

    if (errors.services) {
      setErrors((prev) => ({ ...prev, services: null }));
    }
  };

  const handleRemoveRow = (id) => {
    if (services.length === 1) return;
    setServices((prev) => prev.filter((srv) => srv.id !== id));
  };

  // Xử lý thay đổi khi người dùng chọn dịch vụ từ dropdown SELECT
  const handleSelectServiceOption = (rowId, selectedId) => {
    const selected = serviceOptions.find((opt) => {
      const optId = opt.id || opt.service_item_id || opt.serviceItemId;
      return String(optId) === String(selectedId);
    });

    if (!selected) return;

    setServices((prev) => prev.map((srv) => {
      if (srv.id !== rowId) return srv;
      return {
        ...srv,
        serviceItemId: selected.id || selected.service_item_id || selected.serviceItemId || null,
        serviceName: selected.service_name || selected.serviceName || selected.name || selected.title || '',
        serviceCode: selected.service_code || selected.serviceCode || selected.code || '',
        serviceGroup: selected.service_group || selected.serviceGroup || selected.group || '',
        unit: selected.unit || srv.unit,
        price: formatCurrency(extractPrice(selected))
      };
    }));
  };

  const handleServiceChange = (id, field, value) => {
    setServices((prev) => prev.map((srv) => {
      if (srv.id !== id) return srv;
      if (field === 'price') {
        return { ...srv, price: formatCurrency(value) };
      }
      return { ...srv, [field]: value };
    }));
  };

  const validateForm = () => {
    const newErrors = {};

    if (!formData.priceName.trim()) {
      newErrors.priceName = 'Vui lòng nhập tên bảng giá';
    }

    if (!formData.effectiveFrom) {
      newErrors.effectiveFrom = 'Vui lòng chọn ngày bắt đầu';
    }

    if (!formData.effectiveTo) {
      newErrors.effectiveTo = 'Vui lòng chọn ngày kết thúc';
    } else if (new Date(formData.effectiveTo) <= new Date(formData.effectiveFrom)) {
      newErrors.effectiveTo = 'Ngày kết thúc phải lớn hơn ngày bắt đầu';
    }

    if (services.length === 0) {
      newErrors.services = 'Bảng giá phải có ít nhất 1 dịch vụ';
    } else {
      const invalidRow = services.some(
        (s) => (!s.serviceItemId && !s.serviceCode) || parseCurrency(s.price) <= 0
      );
      if (invalidRow) {
        newErrors.services = 'Tất cả các dòng phải chọn dịch vụ hợp lệ và nhập đơn giá > 0';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
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
    effectiveTo: formData.effectiveTo,
    effective_to: formData.effectiveTo,
    status: statusType,
    version: formData.version,
    services: services.map((s) => ({
      // Đảm bảo gửi chuẩn cả 2 chuẩn đặt tên Snake/Camel case
      serviceItemId: s.serviceItemId,
      service_item_id: s.serviceItemId,
      serviceCode: s.serviceCode,
      service_code: s.serviceCode,
      serviceName: s.serviceName,
      service_name: s.serviceName,
      serviceGroup: s.serviceGroup,
      service_group: s.serviceGroup,
      unit: s.unit,
      price: parseCurrency(s.price),
      unit_price: parseCurrency(s.price)
    }))
  });

  const submitDataToApi = async (statusType) => {
    if (!validateForm()) return;

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
        title: statusType === 'DRAFT' ? 'Đã lưu bản ghi nháp!' : 'Gửi phê duyệt thành công!',
        message: statusType === 'DRAFT'
          ? `Dữ liệu bảng giá ${targetCode} đã lưu thành công ở trạng thái nháp (Draft).`
          : `Bảng giá ${targetCode} đã được tạo ở trạng thái SUBMITTED và chuyển đến cấp Quản lý phê duyệt.`,
        btnText: statusType === 'DRAFT' ? 'Đóng' : 'Xác nhận'
      });
    } catch (error) {
      console.error('Lỗi khi tạo bảng giá:', error);
      setModalConfig({
        isOpen: true,
        type: 'error',
        title: 'Tạo bảng giá thất bại!',
        message: error.message,
        btnText: 'Thử lại'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmModal = () => {
    const isError = modalConfig.type === 'error';
    setModalConfig((prev) => ({ ...prev, isOpen: false }));
    if (!isError) {
      navigate('/staff/price-lists');
    }
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
          <span className="px-3 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-md border border-slate-200 font-mono">
            v{formData.version}
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
              <label className="block text-slate-600 font-medium mb-1.5">
                Tên bảng giá <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                placeholder="Nhập tên bảng giá chi tiết..."
                value={formData.priceName}
                onChange={(e) => {
                  setFormData({ ...formData, priceName: e.target.value });
                  if (errors.priceName) setErrors({ ...errors, priceName: null });
                }}
                className={`w-full px-3 py-2 rounded-lg border focus:outline-none bg-white placeholder:text-slate-400 ${
                  errors.priceName 
                    ? 'border-rose-500 ring-1 ring-rose-500' 
                    : 'border-slate-200 focus:border-sky-500'
                }`}
              />
              {errors.priceName && (
                <p className="text-rose-500 text-[11px] font-medium mt-1">
                  * {errors.priceName}
                </p>
              )}
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
                <option value="SERVICE_GROUP">Nhóm dịch vụ (SERVICE_GROUP)</option>
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
              <label className="block text-slate-600 font-medium mb-1.5">
                Thời gian hiệu lực từ <span className="text-rose-500">*</span>
              </label>
              <input
                type="date"
                value={formData.effectiveFrom}
                onChange={(e) => {
                  setFormData({ ...formData, effectiveFrom: e.target.value });
                  if (errors.effectiveFrom) setErrors({ ...errors, effectiveFrom: null });
                }}
                className={`w-full px-3 py-2 rounded-lg border focus:outline-none bg-white text-slate-700 ${
                  errors.effectiveFrom 
                    ? 'border-rose-500 ring-1 ring-rose-500' 
                    : 'border-slate-200 focus:border-sky-500'
                }`}
              />
              {errors.effectiveFrom && (
                <p className="text-rose-500 text-[11px] font-medium mt-1">
                  * {errors.effectiveFrom}
                </p>
              )}
            </div>

            <div>
              <label className="block text-slate-600 font-medium mb-1.5">
                Thời gian hiệu lực đến <span className="text-rose-500">*</span>
              </label>
              <input
                type="date"
                value={formData.effectiveTo}
                onChange={(e) => {
                  setFormData({ ...formData, effectiveTo: e.target.value });
                  if (errors.effectiveTo) setErrors({ ...errors, effectiveTo: null });
                }}
                className={`w-full px-3 py-2 rounded-lg border focus:outline-none bg-white text-slate-700 ${
                  errors.effectiveTo 
                    ? 'border-rose-500 ring-1 ring-rose-500' 
                    : 'border-slate-200 focus:border-sky-500'
                }`}
              />
              {errors.effectiveTo && (
                <p className="text-rose-500 text-[11px] font-medium mt-1">
                  * {errors.effectiveTo}
                </p>
              )}
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

          {errors.services && (
            <p className="text-rose-500 text-xs font-medium">
              * {errors.services}
            </p>
          )}

          <div className={`border rounded-lg overflow-hidden ${errors.services ? 'border-rose-400' : 'border-slate-200'}`}>
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-semibold">
                  <th className="py-2.5 px-4 w-[30%]">Dịch vụ cung cấp *</th>
                  <th className="py-2.5 px-4 w-[16%]">Mã dịch vụ</th>
                  <th className="py-2.5 px-4 w-[18%]">Nhóm dịch vụ</th>
                  <th className="py-2.5 px-4 w-[10%]">Đơn vị tính</th>
                  <th className="py-2.5 px-4 w-[20%] text-right">Đơn giá định mức *</th>
                  <th className="py-2.5 px-4 w-[6%] text-center">Xóa</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {isLoadingServices ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400 font-medium">
                      <div className="flex justify-center items-center space-x-2">
                        <Loader2 className="w-4 h-4 animate-spin text-[#2b727d]" />
                        <span>Đang tải danh sách dịch vụ từ hệ thống...</span>
                      </div>
                    </td>
                  </tr>
                ) : services.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-400 font-medium">
                      Chưa có dịch vụ nào. Hãy bấm "Thêm dòng dịch vụ".
                    </td>
                  </tr>
                ) : (
                  services.map((service) => {
                    const isRowInvalid = errors.services && (!service.serviceItemId || parseCurrency(service.price) <= 0);
                    return (
                      <tr key={service.id} className={`transition ${isRowInvalid ? 'bg-rose-50/30' : 'hover:bg-slate-50/50'}`}>
                        <td className="py-2.5 px-4">
                          {/* SỬA LỖI: Thay thế input datalist bằng Select chuẩn để luôn giữ serviceItemId */}
                          <select
                            value={service.serviceItemId || ''}
                            onChange={(e) => handleSelectServiceOption(service.id, e.target.value)}
                            className={`w-full px-3 py-1.5 rounded-lg border focus:outline-none bg-white font-medium text-slate-800 ${
                              isRowInvalid && !service.serviceItemId
                                ? 'border-rose-500'
                                : 'border-slate-200 focus:border-sky-500'
                            }`}
                          >
                            <option value="" disabled>-- Chọn dịch vụ --</option>
                            {serviceOptions.map((opt) => {
                              const optId = opt.id || opt.service_item_id || opt.serviceItemId;
                              const optName = opt.service_name || opt.serviceName || opt.name || opt.title;
                              return (
                                <option key={optId} value={optId}>
                                  {optName}
                                </option>
                              );
                            })}
                          </select>
                        </td>

                        <td className="py-2.5 px-4 text-slate-500 font-mono font-medium">
                          <input
                            type="text"
                            readOnly
                            value={service.serviceCode}
                            className="w-full bg-transparent border-b border-transparent font-mono text-slate-600 focus:outline-none"
                          />
                        </td>

                        <td className="py-2.5 px-4 text-slate-600">
                          <input
                            type="text"
                            placeholder="Nhóm dịch vụ..."
                            value={service.serviceGroup}
                            onChange={(e) => handleServiceChange(service.id, 'serviceGroup', e.target.value)}
                            className="w-full bg-transparent border-b border-transparent hover:border-slate-300 focus:border-sky-500 focus:bg-white focus:outline-none"
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
                              inputMode="numeric"
                              value={service.price}
                              onChange={(e) => handleServiceChange(service.id, 'price', e.target.value)}
                              className={`w-32 px-3 py-1.5 rounded-lg border text-right font-bold text-slate-800 focus:outline-none bg-white ${
                                isRowInvalid && parseCurrency(service.price) <= 0 ? 'border-rose-500' : 'border-slate-200 focus:border-sky-500'
                              }`}
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
                    );
                  })
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
                  : modalConfig.type === 'error'
                  ? 'bg-rose-100/70 text-rose-500'
                  : 'bg-emerald-100/70 text-emerald-500'
              }`}>
                {modalConfig.type === 'error' ? (
                  <AlertCircle className="w-8 h-8 stroke-[2.5]" />
                ) : (
                  <Check className="w-8 h-8 stroke-[2.5]" />
                )}
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
                  : modalConfig.type === 'error'
                  ? 'bg-rose-600 hover:bg-rose-700'
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