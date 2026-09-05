import React, { useState } from 'react';

export default function PeriodTable({ periods = [], onRefresh }) {
    const [unlockModal, setUnlockModal] = useState(null);
    const [unlockReason, setUnlockReason] = useState("");
    
    const [confirmLock, setConfirmLock] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const getStatusBadge = (status) => {
        switch(status) {
            case 'LOCKED': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-locked">Đã khóa</span>;
            case 'OPEN': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-unlocked">Đang mở</span>;
            default: return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-600">{status}</span>;
        }
    };

    const submitLock = async () => {
        if (!confirmLock) return;
        setSubmitting(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/${confirmLock}/lock`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                if (onRefresh) onRefresh();
            } else {
                alert('Có lỗi xảy ra khi khóa kỳ!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối server!');
        } finally {
            setSubmitting(false);
            setConfirmLock(null);
        }
    };

    const submitUnlockRequest = async () => {
        if (!unlockReason || !unlockReason.trim()) return;
        setSubmitting(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/${unlockModal}/unlock-request`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}` 
                },
                body: JSON.stringify({ reason: unlockReason })
            });
            if (res.ok) {
                if (onRefresh) onRefresh();
            } else {
                alert('Có lỗi xảy ra hoặc đã tồn tại yêu cầu cho kỳ này!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối server!');
        } finally {
            setSubmitting(false);
            setUnlockModal(null);
            setUnlockReason("");
        }
    };

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 relative">
            <h3 className="text-lg font-bold text-slate-800 mb-2">Danh sách kỳ sản lượng</h3>
            <p className="text-slate-500 text-sm mb-6">Chốt số liệu và khóa kỳ để đồng bộ thanh toán.</p>

            <div className="overflow-x-auto border rounded-lg border-slate-200">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                    <thead>
                        <tr className="bg-slate-50 text-slate-500 text-[11px] uppercase tracking-wider border-b border-slate-200">
                            <th className="px-4 py-3 font-semibold">Kỳ (Tháng)</th>
                            <th className="px-4 py-3 font-semibold">Trạng thái</th>
                            <th className="px-4 py-3 font-semibold">Hành động</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {periods.length > 0 ? periods.map((p) => (
                            <tr key={p.period_key} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-4 py-3 font-medium text-slate-700">{p.period_key}</td>
                                <td className="px-4 py-3">{getStatusBadge(p.status)}</td>
                                <td className="px-4 py-3">
                                    {p.status === 'OPEN' ? (
                                        <button onClick={() => setConfirmLock(p.period_key)} className="text-sm font-medium text-teal-600 hover:text-teal-800">Khóa kỳ</button>
                                    ) : (
                                        <button onClick={() => setUnlockModal(p.period_key)} className="text-sm font-medium text-amber-500 hover:text-amber-600">Xin mở khóa</button>
                                    )}
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="3" className="px-4 py-6 text-center text-slate-500">Chưa có dữ liệu kỳ</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {/* Modal Xin mở khóa */}
            {unlockModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden transform transition-all">
                        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                            <h3 className="font-bold text-slate-800">Xin mở khóa kỳ {unlockModal}</h3>
                            <button onClick={() => { setUnlockModal(null); setUnlockReason(""); }} className="text-slate-400 hover:text-slate-600">
                                <i className="fa-solid fa-xmark"></i>
                            </button>
                        </div>
                        <div className="p-6">
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Lý do xin mở khóa <span className="text-red-500">*</span>
                            </label>
                            <textarea 
                                className="w-full border border-slate-300 rounded-lg p-3 text-sm focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none transition-all"
                                rows="3"
                                placeholder="Nhập lý do chi tiết để Giám đốc phê duyệt..."
                                value={unlockReason}
                                onChange={(e) => setUnlockReason(e.target.value)}
                            ></textarea>
                            
                            <div className="mt-6 flex justify-end space-x-3">
                                <button 
                                    onClick={() => { setUnlockModal(null); setUnlockReason(""); }} 
                                    className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                                >
                                    Hủy
                                </button>
                                <button 
                                    onClick={submitUnlockRequest} 
                                    disabled={!unlockReason.trim() || submitting}
                                    className="px-4 py-2 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                                >
                                    {submitting ? <i className="fa-solid fa-spinner fa-spin mr-2"></i> : <i className="fa-solid fa-paper-plane mr-2"></i>}
                                    Gửi yêu cầu
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal Xác nhận Khóa kỳ */}
            {confirmLock && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-xl w-full max-w-sm overflow-hidden transform transition-all">
                        <div className="p-6 text-center">
                            <div className="w-16 h-16 rounded-full bg-teal-100 flex items-center justify-center mx-auto mb-4 text-teal-600 text-2xl">
                                <i className="fa-solid fa-lock"></i>
                            </div>
                            <h3 className="text-lg font-bold text-slate-800 mb-2">Khóa kỳ {confirmLock}?</h3>
                            <p className="text-sm text-slate-500 mb-6">
                                Bạn có chắc chắn muốn khóa kỳ vận hành này? Không thể tự mở lại sau khi đã khóa, mà phải xin phép Giám đốc.
                            </p>
                            
                            <div className="flex justify-center space-x-3">
                                <button 
                                    onClick={() => setConfirmLock(null)} 
                                    className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                                >
                                    Hủy
                                </button>
                                <button 
                                    onClick={submitLock} 
                                    disabled={submitting}
                                    className="flex-1 px-4 py-2 bg-teal-600 text-white rounded-lg text-sm font-medium hover:bg-teal-700 transition-colors disabled:opacity-50 flex justify-center items-center"
                                >
                                    {submitting ? <i className="fa-solid fa-spinner fa-spin mr-2"></i> : null}
                                    Khóa ngay
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
