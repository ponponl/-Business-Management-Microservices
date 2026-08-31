import React, { useState, useRef, useEffect } from 'react';

export default function RecordVolumeForm({ onCancel, onSubmit }) {
    const [selectedUnit, setSelectedUnit] = useState('');
    const [contracts, setContracts] = useState([]);
    const [services, setServices] = useState([]);
    const [loading, setLoading] = useState(true);
    
    // Sinh mã ngẫu nhiên chống Double Submit, mã này sẽ không đổi trong suốt vòng đời của component
    const idempotencyKey = useRef(crypto.randomUUID());

    useEffect(() => {
        const fetchData = async () => {
            try {
                const token = localStorage.getItem('token') || '';
                const headers = {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                };

                // Production service runs on 8084 on host
                const [contractsRes, servicesRes] = await Promise.all([
                    fetch('http://localhost:8084/api/v1/contracts', { headers }),
                    fetch('http://localhost:8084/api/v1/services', { headers })
                ]);
                
                if (contractsRes.ok) {
                    const data = await contractsRes.json();
                    setContracts(data);
                }
                
                if (servicesRes.ok) {
                    const data = await servicesRes.json();
                    // map to code, name, unit based on pricing service response structure
                    // Assuming pricing service returns { service_code, service_name, default_unit }
                    setServices(data.map(s => ({
                        code: s.service_code || s.code,
                        name: s.service_name || s.name,
                        unit: s.default_unit || s.unit || 'Tự động'
                    })));
                }
            } catch (error) {
                console.error("Error fetching data:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const handleServiceChange = (e) => {
        const serviceCode = e.target.value;
        const srv = services.find(s => s.code === serviceCode);
        setSelectedUnit(srv ? srv.unit : '');
    };

    return (
        <div>
            {/* Header & Back btn */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <button onClick={onCancel} className="text-primary hover:text-teal-800 text-sm font-medium mb-3 flex items-center transition-colors">
                        <i className="fa-solid fa-arrow-left mr-2"></i> Quay lại danh sách
                    </button>
                    <h2 className="text-2xl font-bold text-slate-800">Ghi nhận sản lượng mới</h2>
                </div>
                <div className="flex space-x-3">
                    <button type="button" onClick={onCancel} className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm">
                        Hủy bỏ
                    </button>
                    <button type="button" onClick={onSubmit} className="bg-primary hover:bg-teal-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center">
                        <i className="fa-solid fa-paper-plane mr-2"></i> Lưu dữ liệu
                    </button>
                </div>
            </div>

            <form>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Thông tin chung */}
                    <div className="col-span-2 space-y-6">
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Thông tin chung</h3>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Hợp đồng dịch vụ <span className="text-red-500">*</span></label>
                                <select required className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm">
                                    <option value="">-- Chọn Hợp đồng --</option>
                                    {loading ? (
                                        <option value="" disabled>Đang tải...</option>
                                    ) : (
                                        contracts.map(c => (
                                            <option key={c.contract_number} value={c.contract_number}>
                                                {c.contract_number}
                                            </option>
                                        ))
                                    )}
                                </select>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Chi tiết Dịch vụ</h3>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-700 mb-2">Hạng mục Dịch vụ áp dụng <span className="text-red-500">*</span></label>
                                <select required onChange={handleServiceChange} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm">
                                    <option value="">-- Chọn Dịch vụ --</option>
                                    {loading ? (
                                        <option value="" disabled>Đang tải...</option>
                                    ) : (
                                        services.map(srv => (
                                            <option key={srv.code} value={srv.code}>{srv.name} ({srv.code})</option>
                                        ))
                                    )}
                                </select>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-2">Số lượng thực tế <span className="text-red-500">*</span></label>
                                    <input type="number" min="0.01" step="0.01" required className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm" />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 mb-2">Đơn vị tính</label>
                                    <input type="text" readOnly className="w-full border border-slate-300 bg-slate-50 rounded-lg px-4 py-2.5 outline-none text-sm text-slate-500" value={selectedUnit} placeholder="Tự động" />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Cột phải */}
                    <div className="col-span-1 space-y-6">
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Thời gian</h3>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Ngày vận hành <span className="text-red-500">*</span></label>
                                <input type="date" required className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm" />
                            </div>
                        </div>
                        
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Tệp đính kèm</h3>
                            <p className="text-xs text-slate-500 mb-4">Bạn có thể đính kèm biên bản xác nhận sản lượng (nếu có).</p>
                            <div className="border-2 border-dashed border-slate-300 rounded-lg p-6 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-slate-50 transition-colors">
                                <i className="fa-solid fa-cloud-arrow-up text-3xl text-slate-400 mb-2"></i>
                                <span className="text-sm text-slate-600 font-medium mb-1">Kéo thả tệp vào đây</span>
                                <span className="text-xs text-slate-400">hoặc</span>
                                <button type="button" className="mt-2 text-primary text-sm font-medium hover:underline">Chọn tệp</button>
                            </div>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    );
}
