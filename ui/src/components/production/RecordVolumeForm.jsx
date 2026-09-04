import React, { useState, useRef, useEffect } from 'react';

export default function RecordVolumeForm({ onCancel, onSubmit }) {
    const [selectedUnit, setSelectedUnit] = useState('');
    const [contracts, setContracts] = useState([]);
    const [services, setServices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    
    // Form state
    const [contractId, setContractId] = useState('');
    const [serviceCode, setServiceCode] = useState('');
    const [quantity, setQuantity] = useState('');
    const [volumeDate, setVolumeDate] = useState('');

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
                const res = await fetch('http://localhost:8084/api/v1/contracts', { headers });
                
                if (res.ok) {
                    const data = await res.json();
                    const contractItems = Array.isArray(data)
                        ? data
                        : data?.items || data?.data || [];
                    setContracts(Array.isArray(contractItems) ? contractItems : []);
                } else {
                    setContracts([]);
                }
            } catch (error) {
                console.error("Error fetching data:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    useEffect(() => {
        if (!contractId) {
            setServices([]);
            setServiceCode('');
            setSelectedUnit('');
            return;
        }

        const fetchServices = async () => {
            try {
                const token = localStorage.getItem('token') || '';
                const headers = {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                };
                const res = await fetch(`http://localhost:8084/api/v1/contracts/${contractId}/services`, { headers });
                
                if (res.ok) {
                    const data = await res.json();
                    const serviceItems = Array.isArray(data)
                        ? data
                        : data?.items || data?.data || [];
                    setServices((Array.isArray(serviceItems) ? serviceItems : []).map(s => ({
                        code: s.service_code || s.code,
                        name: s.service_name || s.name,
                        unit: s.default_unit || s.unit || 'Tự động'
                    })));
                } else {
                    setServices([]);
                }
            } catch (error) {
                console.error("Error fetching services:", error);
            }
        };
        fetchServices();
    }, [contractId]);

    const handleServiceChange = (e) => {
        const srvCode = e.target.value;
        setServiceCode(srvCode);
        const srv = services.find(s => s.code === srvCode);
        setSelectedUnit(srv ? srv.unit : '');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setSubmitting(true);

        try {
            const token = localStorage.getItem('token') || '';
            const dateObj = new Date(volumeDate);
            const periodKey = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`;
            
            const payload = {
                contract_id: contractId,
                service_code: serviceCode,
                volume_date: new Date(volumeDate).toISOString(),
                period_key: periodKey,
                quantity: parseFloat(quantity),
                unit: selectedUnit
            };

            const res = await fetch('http://localhost:8084/api/v1/volumes', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    'Idempotency-Key': idempotencyKey.current
                },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Lỗi khi lưu dữ liệu');
            }

            // Success
            onSubmit();
        } catch (err) {
            setError(err.message);
        } finally {
            setSubmitting(false);
        }
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
                    <button type="submit" form="record-volume-form" disabled={submitting} className={`bg-primary hover:bg-teal-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center ${submitting ? 'opacity-70 cursor-not-allowed' : ''}`}>
                        <i className="fa-solid fa-paper-plane mr-2"></i> {submitting ? 'Đang lưu...' : 'Lưu dữ liệu'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-lg border border-red-100 flex items-center">
                    <i className="fa-solid fa-circle-exclamation mr-2"></i>
                    {error}
                </div>
            )}

            <form id="record-volume-form" onSubmit={handleSubmit}>
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Thông tin chung */}
                    <div className="col-span-2 space-y-6">
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Thông tin chung</h3>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Hợp đồng dịch vụ <span className="text-red-500">*</span></label>
                                <select required value={contractId} onChange={e => setContractId(e.target.value)} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm">
                                    <option value="">-- Chọn Hợp đồng --</option>
                                    {loading ? (
                                        <option value="" disabled>Đang tải...</option>
                                    ) : (
                                        contracts.map(c => (
                                            <option key={c.contract_number} value={c.contract_id || c.contract_number}>
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
                                <select required value={serviceCode} onChange={handleServiceChange} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm">
                                    <option value="">-- Chọn Dịch vụ --</option>
                                    {loading ? (
                                        <option value="" disabled>Đang tải...</option>
                                    ) : services.length === 0 && contractId ? (
                                        <option value="" disabled>-- Vui lòng cấu hình Bảng giá cho Hợp đồng này trước --</option>
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
                                    <input type="number" min="0.01" step="0.01" required value={quantity} onChange={e => setQuantity(e.target.value)} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm" />
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
                                <input type="date" required value={volumeDate} onChange={e => setVolumeDate(e.target.value)} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm" />
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
