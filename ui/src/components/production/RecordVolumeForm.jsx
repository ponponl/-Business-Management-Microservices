import React, { useState, useRef, useEffect } from 'react';

export default function RecordVolumeForm({ onCancel, onSubmit }) {
    const [contracts, setContracts] = useState([]);
    const [services, setServices] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);
    
    // Form state
    const [contractId, setContractId] = useState('');
    const [volumeDate, setVolumeDate] = useState('');
    
    // Smart Search state
    const [searchContractQuery, setSearchContractQuery] = useState('');
    const [showContractSuggestions, setShowContractSuggestions] = useState(false);
    const searchRef = useRef(null);
    
    // Items state for multiple services
    const [items, setItems] = useState([
        { id: Date.now(), serviceCode: '', quantity: '', unit: '' }
    ]);

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
                    setContracts(data);
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
        const handleClickOutside = (event) => {
            if (searchRef.current && !searchRef.current.contains(event.target)) {
                setShowContractSuggestions(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const filteredContracts = contracts.filter(c => 
        (c.contract_number || c.contract_id || '').toLowerCase().includes(searchContractQuery.toLowerCase())
    );

    useEffect(() => {
        if (!contractId) {
            setServices([]);
            setItems([{ id: Date.now(), serviceCode: '', quantity: '', unit: '' }]);
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
                    setServices(data.map(s => ({
                        code: s.service_code || s.code,
                        name: s.service_name || s.name,
                        unit: s.default_unit || s.unit || 'Tự động'
                    })));
                }
            } catch (error) {
                console.error("Error fetching services:", error);
            }
        };
        fetchServices();
    }, [contractId]);

    const handleItemChange = (id, field, value) => {
        setItems(prev => prev.map(item => {
            if (item.id === id) {
                const updated = { ...item, [field]: value };
                if (field === 'serviceCode') {
                    const srv = services.find(s => s.code === value);
                    updated.unit = srv ? srv.unit : '';
                }
                return updated;
            }
            return item;
        }));
    };

    const addItem = () => {
        setItems(prev => [...prev, { id: Date.now(), serviceCode: '', quantity: '', unit: '' }]);
    };

    const removeItem = (id) => {
        setItems(prev => {
            if (prev.length === 1) return prev;
            return prev.filter(item => item.id !== id);
        });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        // Validate items
        const invalidItem = items.find(item => !item.serviceCode || !item.quantity);
        if (invalidItem) {
            setError('Vui lòng điền đầy đủ Dịch vụ và Số lượng cho tất cả các dòng.');
            return;
        }

        setSubmitting(true);

        try {
            const token = localStorage.getItem('token') || '';
            const dateObj = new Date(volumeDate);
            const periodKey = `${dateObj.getFullYear()}-${String(dateObj.getMonth() + 1).padStart(2, '0')}`;
            
            const promises = items.map((item, index) => {
                const payload = {
                    contract_id: contractId,
                    service_code: item.serviceCode,
                    volume_date: new Date(volumeDate).toISOString(),
                    period_key: periodKey,
                    quantity: parseFloat(item.quantity),
                    unit: item.unit
                };

                return fetch('http://localhost:8084/api/v1/volumes', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                        'Idempotency-Key': `${idempotencyKey.current}-${index}`
                    },
                    body: JSON.stringify(payload)
                }).then(async res => {
                    if (!res.ok) {
                        const errData = await res.json();
                        throw new Error(`Dòng ${index + 1}: ${errData.detail || 'Lỗi khi lưu dữ liệu'}`);
                    }
                    return res;
                });
            });

            await Promise.all(promises);

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
                    <button onClick={onCancel} type="button" className="text-primary hover:text-teal-800 text-sm font-medium mb-3 flex items-center transition-colors">
                        <i className="fa-solid fa-arrow-left mr-2"></i> Quay lại danh sách
                    </button>
                    <h2 className="text-2xl font-bold text-slate-800">Ghi nhận sản lượng mới</h2>
                </div>
                <div className="flex space-x-3">
                    <button type="button" onClick={onCancel} className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm">
                        Hủy bỏ
                    </button>
                    <button type="button" onClick={handleSubmit} disabled={submitting} className={`bg-primary hover:bg-teal-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center ${submitting ? 'opacity-70 cursor-not-allowed' : ''}`}>
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
                <div className="space-y-6">
                    {/* Top Row: Thông tin chung & Thời gian */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Thông tin chung</h3>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Hợp đồng dịch vụ <span className="text-red-500">*</span></label>
                                <div className="relative" ref={searchRef}>
                                    <input 
                                        type="text" 
                                        placeholder="Tìm kiếm hợp đồng..." 
                                        value={searchContractQuery}
                                        onFocus={() => setShowContractSuggestions(true)}
                                        onChange={(e) => {
                                            setSearchContractQuery(e.target.value);
                                            setShowContractSuggestions(true);
                                            setContractId(''); // reset selection when user types
                                        }}
                                        className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm" 
                                        disabled={loading}
                                        required={!contractId}
                                    />
                                    {loading && <i className="fa-solid fa-spinner fa-spin absolute right-3 top-3 text-slate-400"></i>}
                                    {showContractSuggestions && searchContractQuery && !loading && (
                                        <ul className="absolute z-10 w-full mt-1 bg-white border border-slate-200 rounded-md shadow-lg max-h-48 overflow-auto">
                                            {filteredContracts.length > 0 ? filteredContracts.map(c => (
                                                <li 
                                                    key={c.contract_number}
                                                    className="px-4 py-2 hover:bg-slate-100 cursor-pointer text-sm text-slate-700"
                                                    onClick={() => {
                                                        setContractId(c.contract_id || c.contract_number);
                                                        setSearchContractQuery(c.contract_number);
                                                        setShowContractSuggestions(false);
                                                    }}
                                                >
                                                    {c.contract_number}
                                                </li>
                                            )) : (
                                                <li className="px-4 py-2 text-sm text-slate-500 italic">Không tìm thấy hợp đồng</li>
                                            )}
                                        </ul>
                                    )}
                                    {contractId && !showContractSuggestions && (
                                        <div className="absolute right-3 top-3 text-green-600" title="Đã chọn hợp đồng">
                                            <i className="fa-solid fa-check-circle"></i>
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                            <h3 className="text-base font-bold text-slate-800 mb-4 border-b pb-2">Thời gian</h3>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">Ngày vận hành <span className="text-red-500">*</span></label>
                                <input type="date" required value={volumeDate} onChange={e => setVolumeDate(e.target.value)} className="w-full border border-slate-300 rounded-lg px-4 py-2.5 outline-none focus:border-primary text-sm" />
                            </div>
                        </div>
                    </div>

                    {/* Chi tiết Dịch vụ (Full width) */}
                    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
                        <div className="flex justify-between items-center mb-4 border-b pb-2">
                            <h3 className="text-base font-bold text-slate-800">Chi tiết Dịch vụ</h3>
                            <button 
                                type="button" 
                                onClick={addItem}
                                className="text-sm font-medium text-primary hover:text-teal-800 border border-primary hover:bg-teal-50 px-3 py-1.5 rounded-lg transition-colors flex items-center"
                            >
                                <i className="fa-solid fa-plus mr-2"></i> Thêm dòng dịch vụ
                            </button>
                        </div>
                        
                        <div className="overflow-x-auto">
                            <table className="w-full text-left border-collapse whitespace-nowrap">
                                <thead>
                                    <tr className="border-b border-slate-200 text-slate-500 text-xs uppercase">
                                        <th className="py-3 pr-4 font-semibold w-[40%]">Hạng mục Dịch vụ áp dụng <span className="text-red-500">*</span></th>
                                        <th className="py-3 px-4 font-semibold w-[30%]">Số lượng thực tế <span className="text-red-500">*</span></th>
                                        <th className="py-3 px-4 font-semibold w-[20%]">Đơn vị tính</th>
                                        <th className="py-3 pl-4 font-semibold text-center w-[10%]">Thao tác</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((item, index) => (
                                        <tr key={item.id} className="border-b border-slate-100 last:border-0">
                                            <td className="py-3 pr-4">
                                                <select 
                                                    required 
                                                    value={item.serviceCode} 
                                                    onChange={e => handleItemChange(item.id, 'serviceCode', e.target.value)} 
                                                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:border-primary text-sm"
                                                >
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
                                            </td>
                                            <td className="py-3 px-4">
                                                <input 
                                                    type="number" 
                                                    min="0.01" 
                                                    step="0.01" 
                                                    required 
                                                    value={item.quantity} 
                                                    onChange={e => handleItemChange(item.id, 'quantity', e.target.value)} 
                                                    className="w-full border border-slate-300 rounded-lg px-3 py-2 outline-none focus:border-primary text-sm" 
                                                    placeholder="Nhập số lượng..."
                                                />
                                            </td>
                                            <td className="py-3 px-4">
                                                <input 
                                                    type="text" 
                                                    readOnly 
                                                    className="w-full border border-slate-300 bg-slate-50 rounded-lg px-3 py-2 outline-none text-sm text-slate-500" 
                                                    value={item.unit} 
                                                    placeholder="Tự động" 
                                                />
                                            </td>
                                            <td className="py-3 pl-4 text-center">
                                                <button 
                                                    type="button" 
                                                    onClick={() => removeItem(item.id)}
                                                    disabled={items.length === 1}
                                                    className="text-red-500 hover:text-red-700 disabled:opacity-30 p-2 transition-colors"
                                                    title="Xóa dòng"
                                                >
                                                    <i className="fa-regular fa-trash-can"></i>
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </form>
        </div>
    );
}
