import React from 'react';

export default function UnlockRequestTable({ requests = [] }) {
    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-2">Phê duyệt yêu cầu mở khóa</h3>
            <p className="text-slate-500 text-sm mb-6">Dành cho Ban Giám đốc xử lý các yêu cầu từ nhân viên.</p>

            <div className="overflow-x-auto border rounded-lg border-slate-200">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                    <thead>
                        <tr className="bg-slate-50 text-slate-500 text-[11px] uppercase tracking-wider border-b border-slate-200">
                            <th className="px-4 py-3 font-semibold">Kỳ</th>
                            <th className="px-4 py-3 font-semibold">Người yêu cầu</th>
                            <th className="px-4 py-3 font-semibold">Lý do</th>
                            <th className="px-4 py-3 font-semibold text-right">Phê duyệt</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {requests.length > 0 ? requests.map((req) => (
                            <tr key={req.id} className="border-b border-slate-100 hover:bg-slate-50">
                                <td className="px-4 py-3 font-medium text-slate-700">{req.month}</td>
                                <td className="px-4 py-3 text-slate-600">{req.requester}</td>
                                <td className="px-4 py-3 text-slate-500 truncate max-w-[150px]" title={req.reason}>{req.reason}</td>
                                <td className="px-4 py-3 text-right space-x-2">
                                    <button className="px-2 py-1 bg-teal-50 text-teal-600 hover:bg-teal-100 rounded font-medium text-xs">Duyệt</button>
                                    <button className="px-2 py-1 bg-red-50 text-red-600 hover:bg-red-100 rounded font-medium text-xs">Từ chối</button>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="4" className="px-4 py-6 text-center text-slate-500">Chưa có yêu cầu nào</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
