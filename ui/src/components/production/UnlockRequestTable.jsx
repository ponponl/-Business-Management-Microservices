import React from 'react';

export default function UnlockRequestTable({ requests = [], onRefresh }) {
    const handleAction = async (id, approved) => {
        let reject_reason = null;
        if (!approved) {
            reject_reason = window.prompt("Nhập lý do từ chối:");
            if (reject_reason === null) return; // cancelled
        } else {
            if (!window.confirm("Bạn có chắc chắn muốn duyệt yêu cầu mở khóa này?")) return;
        }

        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`http://localhost:8084/api/v1/periods/unlock-requests/${id}/approve`, {
                method: 'PUT',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}` 
                },
                body: JSON.stringify({ approved, reject_reason })
            });

            if (res.ok) {
                alert(`Đã ${approved ? 'duyệt' : 'từ chối'} yêu cầu thành công!`);
                if (onRefresh) onRefresh();
            } else {
                alert('Có lỗi xảy ra khi xử lý yêu cầu!');
            }
        } catch (e) {
            console.error(e);
            alert('Lỗi kết nối server!');
        }
    };

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-2">Phê duyệt yêu cầu mở khóa</h3>
            <p className="text-slate-500 text-sm mb-6">Dành cho Ban Giám đốc xử lý các yêu cầu từ nhân viên.</p>

            <div className="overflow-x-auto border rounded-lg border-slate-200">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                    <thead>
                        <tr className="bg-slate-50 text-slate-500 text-[11px] uppercase tracking-wider border-b border-slate-200">
                            <th className="px-4 py-3 font-semibold">Kỳ</th>
                            <th className="px-4 py-3 font-semibold">Đối tượng</th>
                            <th className="px-4 py-3 font-semibold">Thay đổi</th>
                            <th className="px-4 py-3 font-semibold">Người yêu cầu</th>
                            <th className="px-4 py-3 font-semibold">Lý do</th>
                            <th className="px-4 py-3 font-semibold text-center">Trạng thái</th>
                            <th className="px-4 py-3 font-semibold text-right">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {requests.length > 0 ? requests.map((req) => (
                            <tr key={req.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-4 py-3 font-medium text-slate-700">{req.period_key}</td>
                                <td className="px-4 py-3 text-slate-600">
                                    {req.target_type === 'VOLUME' ? (
                                        <span className="font-medium text-slate-700">{req.target_service_code}</span>
                                    ) : (
                                        'Toàn bộ kỳ'
                                    )}
                                </td>
                                <td className="px-4 py-3 text-slate-600">
                                    {req.target_type === 'VOLUME' ? (
                                        <span className="flex items-center space-x-2 whitespace-nowrap">
                                            <span className="line-through text-slate-400">{req.old_quantity}</span>
                                            <i className="fa-solid fa-arrow-right text-[10px] text-slate-400"></i>
                                            <span className="font-bold text-primary">{req.proposed_quantity}</span>
                                        </span>
                                    ) : (
                                        '—'
                                    )}
                                </td>
                                <td className="px-4 py-3 text-slate-600">{req.requested_by}</td>
                                <td className="px-4 py-3 text-slate-500 truncate max-w-[150px]" title={req.reason}>{req.reason}</td>
                                <td className="px-4 py-3 text-center">
                                    {req.status === 'PENDING' ? (
                                        <span className="px-2 py-1 text-xs font-semibold rounded-md bg-amber-50 text-amber-600">Chờ duyệt</span>
                                    ) : req.status === 'APPROVED' ? (
                                        <span className="px-2 py-1 text-xs font-semibold rounded-md bg-teal-50 text-teal-600">Đã duyệt</span>
                                    ) : (
                                        <span className="px-2 py-1 text-xs font-semibold rounded-md bg-red-50 text-red-600">Đã từ chối</span>
                                    )}
                                </td>
                                <td className="px-4 py-3 text-right space-x-2">
                                    {req.status === 'PENDING' ? (
                                        <>
                                            <button onClick={() => handleAction(req.id, true)} className="px-2 py-1 bg-teal-50 text-teal-600 hover:bg-teal-100 rounded font-medium text-xs">Duyệt</button>
                                            <button onClick={() => handleAction(req.id, false)} className="px-2 py-1 bg-red-50 text-red-600 hover:bg-red-100 rounded font-medium text-xs">Từ chối</button>
                                        </>
                                    ) : (
                                        <span className="text-slate-400 text-xs">—</span>
                                    )}
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="7" className="px-4 py-6 text-center text-slate-500">Chưa có yêu cầu nào</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
