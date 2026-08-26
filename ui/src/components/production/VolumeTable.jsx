import React from 'react';

export default function VolumeTable({ volumes = [] }) {
    const getStatusBadge = (status) => {
        switch(status) {
            case 'LOCKED': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-locked">Đã khóa</span>;
            case 'UNLOCKED': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-unlocked">Chưa khóa</span>;
            case 'PENDING': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-pending">Chờ mở khóa</span>;
            case 'DRAFT': return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-draft">Bản nháp</span>;
            default: return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-600">{status}</span>;
        }
    };

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {/* Filters */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
                <div className="flex items-center space-x-3">
                    <select className="border border-slate-300 rounded-md text-sm px-3 py-2 bg-white text-slate-700 outline-none focus:border-primary">
                        <option value="">Khách hàng: Tất cả</option>
                    </select>
                    <select className="border border-slate-300 rounded-md text-sm px-3 py-2 bg-white text-slate-700 outline-none focus:border-primary">
                        <option value="">Tháng: Tất cả</option>
                    </select>
                    
                    {/* Status Chips */}
                    <div className="flex bg-slate-50 border border-slate-200 rounded-md overflow-hidden p-1 space-x-1 ml-2">
                        <button className="px-3 py-1.5 text-xs font-medium rounded bg-white shadow-sm border border-slate-200 text-teal-700">Tất cả</button>
                        <button className="px-3 py-1.5 text-xs font-medium rounded text-slate-500 hover:bg-slate-100">Đã khóa</button>
                        <button className="px-3 py-1.5 text-xs font-medium rounded text-slate-500 hover:bg-slate-100">Chưa khóa</button>
                    </div>
                </div>
                
                {/* Search & Export */}
                <div className="flex items-center space-x-3">
                    <div className="relative w-64">
                        <i className="fa-solid fa-search absolute left-3 top-2.5 text-slate-400 text-sm"></i>
                        <input type="text" placeholder="Tìm kiếm dịch vụ..." className="w-full border border-slate-300 rounded-md pl-9 pr-3 py-2 text-sm outline-none focus:border-primary bg-white" />
                    </div>
                    <button className="px-3 py-2 border border-slate-300 rounded-md text-sm hover:bg-slate-50 font-medium text-slate-600" title="Xuất Excel">
                        <i className="fa-solid fa-download"></i>
                    </button>
                </div>
            </div>

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                    <thead>
                        <tr className="bg-white text-slate-500 text-[11px] uppercase tracking-wider border-b border-slate-200">
                            <th className="px-6 py-4 font-semibold">Mã ID</th>
                            <th className="px-6 py-4 font-semibold">Khách hàng</th>
                            <th className="px-6 py-4 font-semibold">Ngày VH</th>
                            <th className="px-6 py-4 font-semibold">Dịch vụ</th>
                            <th className="px-6 py-4 font-semibold text-right">Sản lượng</th>
                            <th className="px-6 py-4 font-semibold text-center">Trạng thái</th>
                            <th className="px-6 py-4 font-semibold">Người xử lý</th>
                            <th className="px-6 py-4 font-semibold text-right">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {volumes.length > 0 ? volumes.map((v) => (
                            <tr key={v.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                                <td className="px-6 py-4 font-medium text-slate-700">{v.id}</td>
                                <td className="px-6 py-4">{v.customerName}</td>
                                <td className="px-6 py-4 text-slate-500">{v.date}</td>
                                <td className="px-6 py-4">{v.serviceName}</td>
                                <td className="px-6 py-4 text-right font-semibold text-primary">{v.quantity} {v.unit}</td>
                                <td className="px-6 py-4 text-center">{getStatusBadge(v.status)}</td>
                                <td className="px-6 py-4 text-slate-500">{v.handler}</td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button className="text-slate-400 hover:text-primary transition-colors" title="Chỉnh sửa"><i className="fa-solid fa-pen-to-square"></i></button>
                                    <button className="text-slate-400 hover:text-amber-500 transition-colors" title="Xin mở khóa"><i className="fa-solid fa-unlock-keyhole"></i></button>
                                    <button className="text-slate-400 hover:text-slate-600 transition-colors" title="Lịch sử"><i className="fa-solid fa-clock-rotate-left"></i></button>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="8" className="px-6 py-10 text-center text-slate-500">
                                    Không có dữ liệu sản lượng nào
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
            
            {/* Pagination */}
            <div className="p-4 border-t border-slate-200 flex items-center justify-between text-sm text-slate-500 bg-white">
                <div>Hiển thị {volumes.length} bản ghi</div>
                <div className="flex space-x-1">
                    <button className="w-8 h-8 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50"><i className="fa-solid fa-chevron-left text-xs"></i></button>
                    <button className="w-8 h-8 rounded bg-sidebar text-white flex items-center justify-center font-medium">1</button>
                    <button className="w-8 h-8 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50"><i className="fa-solid fa-chevron-right text-xs"></i></button>
                </div>
            </div>
        </div>
    );
}
