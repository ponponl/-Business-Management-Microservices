import React, { useState, useMemo } from 'react';
import { EditVolumeModal, UnlockVolumeModal, HistoryModal } from './VolumeModals';

export default function VolumeTable({ volumes = [], onRefresh }) {
    const [filterStatus, setFilterStatus] = useState('ALL');
    const [filterMonth, setFilterMonth] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const itemsPerPage = 10;
    const userRole = localStorage.getItem('user_role');

    // Modal states
    const [editVolume, setEditVolume] = useState(null);
    const [unlockVolume, setUnlockVolume] = useState(null);
    const [historyVolume, setHistoryVolume] = useState(null);

    const months = useMemo(() => {
        const mSet = new Set(volumes.map(v => {
            const d = new Date(v.volume_date);
            return `${d.getMonth() + 1}/${d.getFullYear()}`;
        }));
        return Array.from(mSet).sort();
    }, [volumes]);

    const filteredVolumes = volumes.filter(v => {
        const isLocked = v.is_locked;
        if (filterStatus === 'LOCKED' && !isLocked) return false;
        if (filterStatus === 'UNLOCKED' && isLocked) return false; 
        
        if (filterMonth) {
            const d = new Date(v.volume_date);
            const mStr = `${d.getMonth() + 1}/${d.getFullYear()}`;
            if (mStr !== filterMonth) return false;
        }
        
        return true;
    }).sort((a, b) => {
        // 1. Trạng thái: Chưa khóa (is_locked = false) lên trước
        if (a.is_locked !== b.is_locked) {
            return a.is_locked ? 1 : -1;
        }
        // 2. Ngày VH: Mới nhất lên trước (giảm dần)
        return new Date(b.volume_date) - new Date(a.volume_date);
    });

    // Pagination calculations
    const totalPages = Math.ceil(filteredVolumes.length / itemsPerPage) || 1;
    // Ensure current page is valid when filtering changes
    if (currentPage > totalPages) {
        setCurrentPage(totalPages);
    }
    const paginatedVolumes = filteredVolumes.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

    const getStatusBadge = (isLocked) => {
        if (isLocked) return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-locked">Đã khóa</span>;
        return <span className="px-2 py-1 text-xs font-semibold rounded-md badge-unlocked">Chưa khóa</span>;
    };

    return (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            {/* Filters */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-white">
                <div className="flex items-center space-x-3">
                    <select 
                        value={filterMonth}
                        onChange={(e) => { setFilterMonth(e.target.value); setCurrentPage(1); }}
                        className="border border-slate-300 rounded-md text-sm px-3 py-2 bg-white text-slate-700 outline-none focus:border-primary"
                    >
                        <option value="">Tháng: Tất cả</option>
                        {months.map(m => (
                            <option key={m} value={m}>Tháng {m}</option>
                        ))}
                    </select>
                    
                    {/* Status Chips */}
                    <div className="flex bg-slate-50 border border-slate-200 rounded-md overflow-hidden p-1 space-x-1 ml-2">
                        <button 
                            onClick={() => { setFilterStatus('ALL'); setCurrentPage(1); }}
                            className={`px-3 py-1.5 text-xs font-medium rounded border ${filterStatus === 'ALL' ? 'bg-white shadow-sm border-slate-200 text-teal-700' : 'border-transparent text-slate-500 hover:bg-slate-100'}`}
                        >
                            Tất cả
                        </button>
                        <button 
                            onClick={() => { setFilterStatus('LOCKED'); setCurrentPage(1); }}
                            className={`px-3 py-1.5 text-xs font-medium rounded border ${filterStatus === 'LOCKED' ? 'bg-white shadow-sm border-slate-200 text-teal-700' : 'border-transparent text-slate-500 hover:bg-slate-100'}`}
                        >
                            Đã khóa
                        </button>
                        <button 
                            onClick={() => { setFilterStatus('UNLOCKED'); setCurrentPage(1); }}
                            className={`px-3 py-1.5 text-xs font-medium rounded border ${filterStatus === 'UNLOCKED' ? 'bg-white shadow-sm border-slate-200 text-teal-700' : 'border-transparent text-slate-500 hover:bg-slate-100'}`}
                        >
                            Chưa khóa
                        </button>
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
                            <th className="px-6 py-4 font-semibold">Hợp đồng</th>
                            <th className="px-6 py-4 font-semibold">Ngày VH</th>
                            <th className="px-6 py-4 font-semibold">Dịch vụ</th>
                            <th className="px-6 py-4 font-semibold text-right">Sản lượng</th>
                            <th className="px-6 py-4 font-semibold text-center">Trạng thái</th>
                            <th className="px-6 py-4 font-semibold">Người xử lý</th>
                            <th className="px-6 py-4 font-semibold text-right">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {paginatedVolumes.length > 0 ? paginatedVolumes.map((v) => (
                            <tr key={v.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                                <td className="px-6 py-4 font-medium text-slate-700">{v.id}</td>
                                <td className="px-6 py-4 font-semibold text-slate-600">{v.contract_id}</td>
                                <td className="px-6 py-4 text-slate-500">{new Date(v.volume_date).toLocaleDateString('vi-VN')}</td>
                                <td className="px-6 py-4">{v.service_code}</td>
                                <td className="px-6 py-4 text-right font-semibold text-primary">{v.quantity} {v.unit}</td>
                                <td className="px-6 py-4 text-center">{getStatusBadge(v.is_locked)}</td>
                                <td className="px-6 py-4 text-slate-500">{v.recorded_by}</td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button 
                                        onClick={() => setEditVolume(v)} 
                                        disabled={v.is_locked}
                                        className={`transition-colors ${v.is_locked ? 'text-slate-200 cursor-not-allowed' : 'text-slate-400 hover:text-primary'}`} 
                                        title={v.is_locked ? 'Đã khóa' : 'Chỉnh sửa'}
                                    >
                                        <i className="fa-solid fa-pen-to-square"></i>
                                    </button>
                                    <button 
                                        onClick={() => setUnlockVolume(v)}
                                        disabled={!v.is_locked || ['DIRECTOR', 'STAFF', 'OPERATION_STAFF'].includes(userRole)}
                                        className={`transition-colors ${(!v.is_locked || ['DIRECTOR', 'STAFF', 'OPERATION_STAFF'].includes(userRole)) ? 'text-slate-200 cursor-not-allowed' : 'text-slate-400 hover:text-amber-500'}`} 
                                        title={!v.is_locked ? 'Chưa khóa' : (['DIRECTOR', 'STAFF', 'OPERATION_STAFF'].includes(userRole) ? 'Không có quyền' : 'Xin sửa sản lượng')}
                                    >
                                        <i className="fa-solid fa-unlock-keyhole"></i>
                                    </button>
                                    <button 
                                        onClick={() => setHistoryVolume(v)}
                                        className="text-slate-400 hover:text-slate-600 transition-colors" 
                                        title="Lịch sử"
                                    >
                                        <i className="fa-solid fa-clock-rotate-left"></i>
                                    </button>
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
                <div>
                    Hiển thị {paginatedVolumes.length > 0 ? (currentPage - 1) * itemsPerPage + 1 : 0} 
                    - {Math.min(currentPage * itemsPerPage, filteredVolumes.length)} 
                    trong số {filteredVolumes.length} bản ghi
                </div>
                <div className="flex space-x-1">
                    <button 
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="w-8 h-8 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent"
                    >
                        <i className="fa-solid fa-chevron-left text-xs"></i>
                    </button>
                    <button className="w-8 h-8 rounded bg-sidebar text-white flex items-center justify-center font-medium">
                        {currentPage}
                    </button>
                    <button 
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="w-8 h-8 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50 disabled:opacity-50 disabled:hover:bg-transparent"
                    >
                        <i className="fa-solid fa-chevron-right text-xs"></i>
                    </button>
                </div>
            </div>

            {/* Modals */}
            <EditVolumeModal isOpen={!!editVolume} onClose={() => setEditVolume(null)} volume={editVolume} onRefresh={onRefresh} />
            <UnlockVolumeModal isOpen={!!unlockVolume} onClose={() => setUnlockVolume(null)} volume={unlockVolume} onRefresh={onRefresh} />
            <HistoryModal isOpen={!!historyVolume} onClose={() => setHistoryVolume(null)} volume={historyVolume} />
        </div>
    );
}
