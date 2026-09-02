import React, { useState, useEffect, useRef } from 'react';

// Common Modal Backdrop
const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
        <div className="fixed inset-0 bg-slate-900/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                    <h3 className="font-semibold text-slate-800">{title}</h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
                        <i className="fa-solid fa-xmark"></i>
                    </button>
                </div>
                <div className="p-6">
                    {children}
                </div>
            </div>
        </div>
    );
};

export const EditVolumeModal = ({ isOpen, onClose, volume, onRefresh }) => {
    const [quantity, setQuantity] = useState('');
    const [unit, setUnit] = useState('');
    const [serviceCode, setServiceCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [services, setServices] = useState([]);
    const [loadingServices, setLoadingServices] = useState(false);

    useEffect(() => {
        if (volume) {
            setQuantity(volume.quantity);
            setUnit(volume.unit);
            setServiceCode(volume.service_code || '');
        }
    }, [volume]);

    useEffect(() => {
        if (isOpen) {
            const fetchServices = async () => {
                try {
                    setLoadingServices(true);
                    const token = localStorage.getItem('token');
                    const res = await fetch(`http://localhost:8084/api/v1/contracts/${volume.contract_id}/services`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        setServices(data.map(s => ({
                            code: s.service_code || s.code,
                            name: s.service_name || s.name,
                            unit: s.default_unit || s.unit || 'Tự động'
                        })));
                    }
                } catch (err) {
                    console.error('Error fetching services:', err);
                } finally {
                    setLoadingServices(false);
                }
            };
            fetchServices();
        }
    }, [isOpen]);

    const handleServiceChange = (e) => {
        const code = e.target.value;
        setServiceCode(code);
        const srv = services.find(s => s.code === code);
        if (srv && srv.unit && srv.unit !== 'Tự động') {
            setUnit(srv.unit);
        }
    };

    const handleSave = async () => {
        if (!volume) return;
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/volumes/${volume.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    quantity: parseFloat(quantity),
                    unit: unit,
                    service_code: serviceCode
                })
            });
            if (res.ok) {
                onRefresh();
                onClose();
            } else {
                alert('Có lỗi xảy ra khi cập nhật!');
            }
        } catch (error) {
            console.error(error);
            alert('Lỗi kết nối server!');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Sửa sản lượng #${volume?.id}`}>
            <div className="space-y-4">
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Mã dịch vụ</label>
                    <select 
                        value={serviceCode} 
                        onChange={handleServiceChange} 
                        className="w-full border border-slate-300 rounded-md px-3 py-2 focus:border-primary outline-none"
                    >
                        <option value="">-- Chọn Dịch vụ --</option>
                        {loadingServices ? (
                            <option value="" disabled>Đang tải...</option>
                        ) : (
                            services.map(srv => (
                                <option key={srv.code} value={srv.code}>{srv.name} ({srv.code})</option>
                            ))
                        )}
                    </select>
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Sản lượng mới</label>
                    <input type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-full border border-slate-300 rounded-md px-3 py-2 focus:border-primary outline-none" />
                </div>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Đơn vị</label>
                    <input type="text" value={unit} onChange={(e) => setUnit(e.target.value)} className="w-full border border-slate-300 rounded-md px-3 py-2 focus:border-primary outline-none" />
                </div>
                <div className="pt-4 flex justify-end space-x-3">
                    <button onClick={onClose} className="px-4 py-2 border border-slate-300 rounded-md text-slate-700 hover:bg-slate-50 font-medium">Hủy</button>
                    <button onClick={handleSave} disabled={loading} className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 font-medium disabled:opacity-50">Lưu thay đổi</button>
                </div>
            </div>
        </Modal>
    );
};

export const UnlockRequestModal = ({ isOpen, onClose, volume, onRefresh }) => {
    const [reason, setReason] = useState('');
    const [loading, setLoading] = useState(false);
    const idempotencyKey = useRef(null);

    useEffect(() => {
        if (isOpen) {
            idempotencyKey.current = crypto.randomUUID();
        }
    }, [isOpen]);

    const handleSubmit = async () => {
        if (!volume || !reason.trim()) return;
        setLoading(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/${volume.period_key}/unlock-request`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Idempotency-Key': idempotencyKey.current
                },
                body: JSON.stringify({ reason })
            });
            if (res.ok) {
                alert('Đã gửi yêu cầu mở khóa kỳ ' + volume.period_key);
                onClose();
            } else {
                alert('Có lỗi xảy ra ');
            }
        } catch (error) {
            console.error(error);
            alert('Lỗi kết nối server!');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Xin mở khóa kỳ ${volume?.period_key}`}>
            <div className="space-y-4">
                <p className="text-sm text-slate-600">Bạn đang yêu cầu mở khóa kỳ hoạt động chứa bản ghi này. Vui lòng nhập lý do hợp lệ.</p>
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Lý do xin mở khóa</label>
                    <textarea value={reason} onChange={(e) => setReason(e.target.value)} className="w-full border border-slate-300 rounded-md px-3 py-2 focus:border-amber-500 outline-none min-h-[100px]" placeholder="Nhập lý do chi tiết..." />
                </div>
                <div className="pt-4 flex justify-end space-x-3">
                    <button onClick={onClose} className="px-4 py-2 border border-slate-300 rounded-md text-slate-700 hover:bg-slate-50 font-medium">Hủy</button>
                    <button onClick={handleSubmit} disabled={loading || !reason.trim()} className="px-4 py-2 bg-amber-500 text-white rounded-md hover:bg-amber-600 font-medium disabled:opacity-50">Gửi yêu cầu</button>
                </div>
            </div>
        </Modal>
    );
};

export const HistoryModal = ({ isOpen, onClose, volume }) => {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (isOpen && volume) {
            const fetchLogs = async () => {
                setLoading(true);
                try {
                    const token = localStorage.getItem('token');
                    const res = await fetch(`http://localhost:8084/api/v1/volumes/${volume.id}/audit-logs`, {
                        headers: {
                            'Authorization': `Bearer ${token}`
                        }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        setLogs(data);
                    }
                } catch (error) {
                    console.error(error);
                } finally {
                    setLoading(false);
                }
            };
            fetchLogs();
        }
    }, [isOpen, volume]);

    return (
        <Modal isOpen={isOpen} onClose={onClose} title={`Lịch sử dòng #${volume?.id}`}>
            {loading ? (
                <div className="py-10 flex justify-center"><div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div></div>
            ) : logs.length === 0 ? (
                <div className="py-10 text-center text-slate-500">Chưa có lịch sử thay đổi nào.</div>
            ) : (
                <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                    {logs.map((log) => {
                        let parsedNew = {};
                        let parsedOld = {};
                        try {
                            if (log.new_data) parsedNew = JSON.parse(log.new_data);
                            if (log.old_data) parsedOld = JSON.parse(log.old_data);
                        } catch (e) { }

                        return (
                            <div key={log.id} className="border-l-2 border-primary pl-4 py-1">
                                <div className="flex justify-between items-start">
                                    <span className="font-semibold text-slate-800 text-sm">
                                        {log.action === 'CREATE' ? 'Tạo mới' : log.action === 'UPDATE' ? 'Cập nhật' : log.action}
                                    </span>
                                    <span className="text-xs text-slate-400">
                                        {new Date(log.created_at).toLocaleString('vi-VN')}
                                    </span>
                                </div>
                                <div className="text-sm text-slate-600 mt-1">
                                    Bởi: <span className="font-medium text-slate-700">{log.actor_id}</span>
                                </div>

                                {log.action === 'CREATE' && Object.keys(parsedNew).length > 0 && (
                                    <div className="mt-2 bg-slate-50 rounded p-2 text-xs font-mono text-slate-600">
                                        {Object.entries(parsedNew).map(([k, v]) => (
                                            <div key={k}>{k}: {JSON.stringify(v)}</div>
                                        ))}
                                    </div>
                                )}

                                {log.action === 'UPDATE' && Object.keys(parsedNew).length > 0 && (
                                    <div className="mt-2 bg-slate-50 rounded p-2 text-xs font-mono text-slate-600">
                                        {Object.entries(parsedNew).map(([k, v]) => (
                                            <div key={k}>
                                                {k}: <span className="line-through text-red-400 mr-2">{JSON.stringify(parsedOld[k])}</span>
                                                <i className="fa-solid fa-arrow-right text-slate-400 mx-1 text-[10px]"></i>
                                                <span className="text-green-600">{JSON.stringify(v)}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </Modal>
    );
};

export const UnlockVolumeModal = ({ isOpen, onClose, volume, onRefresh }) => {
    const [reason, setReason] = useState('');
    const [proposedQuantity, setProposedQuantity] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const idempotencyKey = useRef(null);

    useEffect(() => {
        if (isOpen && volume) {
            setProposedQuantity(volume.quantity);
            setReason('');
            setError(null);
            idempotencyKey.current = crypto.randomUUID();
        }
    }, [isOpen, volume]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/${volume.period_key}/unlock-request`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                    'Idempotency-Key': idempotencyKey.current
                },
                body: JSON.stringify({
                    reason,
                    target_type: 'VOLUME',
                    target_volume_id: volume.id,
                    target_service_code: volume.service_code,
                    old_quantity: volume.quantity,
                    proposed_quantity: parseFloat(proposedQuantity)
                })
            });

            if (res.ok) {
                onRefresh();
                onClose();
            } else {
                const data = await res.json();
                setError(data.detail || 'Có lỗi xảy ra khi gửi yêu cầu');
            }
        } catch (err) {
            setError('Lỗi kết nối máy chủ');
        } finally {
            setLoading(false);
        }
    };

    if (!volume) return null;

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Yêu cầu sửa sản lượng">
            <form onSubmit={handleSubmit} className="space-y-4">
                {error && <div className="p-3 bg-red-50 text-red-600 rounded text-sm">{error}</div>}
                
                <div className="bg-slate-50 p-3 rounded border border-slate-200">
                    <div className="text-sm text-slate-500 mb-1">Dòng dữ liệu</div>
                    <div className="font-medium text-slate-800">
                        {volume.service_code} ({volume.period_key})
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Sản lượng hiện tại</label>
                        <div className="w-full px-3 py-2 border border-slate-300 rounded bg-slate-100 text-slate-500">
                            {volume.quantity} {volume.unit}
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-1">Sản lượng mới đề xuất *</label>
                        <div className="flex items-center">
                            <input
                                type="number"
                                step="0.01"
                                required
                                value={proposedQuantity}
                                onChange={(e) => setProposedQuantity(e.target.value)}
                                className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                            />
                            <span className="ml-2 text-slate-500">{volume.unit}</span>
                        </div>
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Lý do xin sửa *</label>
                    <textarea
                        required
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        placeholder="Nhập lý do chi tiết..."
                        className="w-full px-3 py-2 border border-slate-300 rounded focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary h-24"
                    />
                </div>

                <div className="pt-4 flex justify-end space-x-3">
                    <button
                        type="button"
                        onClick={onClose}
                        className="px-4 py-2 border border-slate-300 text-slate-700 rounded hover:bg-slate-50 font-medium"
                    >
                        Hủy
                    </button>
                    <button
                        type="submit"
                        disabled={loading}
                        className="px-4 py-2 bg-amber-500 text-white rounded hover:bg-amber-600 font-medium flex items-center"
                    >
                        {loading ? <i className="fa-solid fa-spinner fa-spin mr-2"></i> : <i className="fa-solid fa-paper-plane mr-2"></i>}
                        Gửi yêu cầu
                    </button>
                </div>
            </form>
        </Modal>
    );
};
