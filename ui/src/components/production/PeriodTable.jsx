import React from 'react';

export default function PeriodTable({ periods = [] }) {
    const getStatusBadge = (status) => {
        switch(status) {
            case 'LOCKED': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-locked">Đã khóa</span>;
            case 'UNLOCKED': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-unlocked">Đang mở</span>;
            default: return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-600">{status}</span>;
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
                                <td className="px-4 py-3 font-medium text-slate-700">{p.month}</td>
                                <td className="px-4 py-3">{getStatusBadge(p.status)}</td>
                                <td className="px-4 py-3">
                                    {p.status === 'UNLOCKED' ? (
                                        <button className="text-sm font-medium text-teal-600 hover:text-teal-800">Khóa kỳ</button>
                                    ) : (
                                        <button className="text-sm font-medium text-slate-400 hover:text-amber-600">Mở khóa</button>
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
