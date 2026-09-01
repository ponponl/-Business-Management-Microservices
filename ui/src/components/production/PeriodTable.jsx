import React from 'react';

export default function PeriodTable({ periods = [], onRefresh }) {
    const getStatusBadge = (status) => {
        switch(status) {
            case 'LOCKED': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-locked">Đã khóa</span>;
            case 'OPEN': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-unlocked">Đang mở</span>;
            default: return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-600">{status}</span>;
        }
    };

    const handleLock = async (period_key) => {
        if (!window.confirm(`Bạn có chắc muốn KHÓA kỳ ${period_key}? Không thể tự mở lại sau khi khóa.`)) return;
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/${period_key}/lock`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                alert(`Đã khóa kỳ ${period_key} thành công!`);
                if (onRefresh) onRefresh();
            } else {
                alert('Có lỗi xảy ra khi khóa kỳ!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối server!');
        }
    };

    const handleUnlockRequest = async (period_key) => {
        const reason = window.prompt(`Nhập lý do xin mở khóa kỳ ${period_key}:`);
        if (!reason || !reason.trim()) return;
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/${period_key}/unlock-request`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}` 
                },
                body: JSON.stringify({ reason })
            });
            if (res.ok) {
                alert(`Đã gửi yêu cầu mở khóa kỳ ${period_key} đến Giám đốc!`);
                if (onRefresh) onRefresh();
            } else {
                alert('Có lỗi xảy ra hoặc đã tồn tại yêu cầu cho kỳ này!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối server!');
        }
    };

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
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
                            <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-4 py-3 font-medium text-slate-700">{p.period_key}</td>
                                <td className="px-4 py-3">{getStatusBadge(p.status)}</td>
                                <td className="px-4 py-3">
                                    {p.status === 'OPEN' ? (
                                        <button onClick={() => handleLock(p.period_key)} className="text-sm font-medium text-teal-600 hover:text-teal-800">Khóa kỳ</button>
                                    ) : (
                                        <button onClick={() => handleUnlockRequest(p.period_key)} className="text-sm font-medium text-amber-500 hover:text-amber-600">Xin mở khóa</button>
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
        </div>
    );
}
