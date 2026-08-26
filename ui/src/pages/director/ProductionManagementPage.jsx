import React, { useState } from 'react';
import StatCard from '../../components/production/StatCard';
import VolumeTable from '../../components/production/VolumeTable';
import UnlockRequestTable from '../../components/production/UnlockRequestTable';

export default function ProductionManagementDirectorPage({ user }) {
    const [currentView, setCurrentView] = useState('list'); // 'list' | 'approvals'

    // Mock data for initial UI check
    const mockVolumes = [
        { id: 'VOL-1001', customerName: 'Công ty XNK Bình Dương', date: '2026-08-25', serviceName: 'Xếp dỡ Container 20feet', quantity: 50, unit: 'Cont', status: 'LOCKED', handler: 'Nguyễn Văn A' },
    ];

    const mockRequests = [
        { id: 'REQ-1', month: '07/2026', requester: 'Nguyễn Văn A (Staff)', reason: 'Khách hàng điều chỉnh lại số lượng container xuất tàu 20/07.' },
        { id: 'REQ-2', month: '06/2026', requester: 'Lê Thị C (Staff)', reason: 'Sai sót nhập liệu cân băng tải ngày 15/06.' }
    ];

    const handleSwitchView = (view) => setCurrentView(view);

    return (
        <div className="p-8">
            {currentView === 'list' && (
                <>
                    {/* Page Title */}
                    <div className="flex justify-between items-start mb-8">
                        <div>
                            <h2 className="text-2xl font-bold text-slate-800 mb-1">Quản lý sản lượng (Director)</h2>
                            <p className="text-slate-500 text-sm">Theo dõi tổng quan và phê duyệt các yêu cầu mở khóa kỳ.</p>
                        </div>
                        <div className="flex space-x-3">
                            <button onClick={() => handleSwitchView('approvals')} className="bg-amber-50 border border-amber-200 hover:bg-amber-100 text-amber-700 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center shadow-sm">
                                <i className="fa-solid fa-bell mr-2"></i> Phê duyệt yêu cầu ({mockRequests.length})
                            </button>
                        </div>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <StatCard title="Tổng bản ghi" value="1" icon="fa-regular fa-folder" colorClass="bg-slate-100 text-slate-500" />
                        <StatCard title="Sản lượng Container" value="50" icon="fa-solid fa-box" colorClass="bg-amber-50 text-amber-500" />
                        <StatCard title="Sản lượng Hàng rời" value="0" icon="fa-solid fa-weight-hanging" colorClass="bg-green-50 text-green-500" />
                        <StatCard title="Yêu cầu chờ duyệt" value={mockRequests.length} icon="fa-solid fa-bell" colorClass="bg-amber-50 text-amber-500" />
                    </div>

                    {/* Table */}
                    <VolumeTable volumes={mockVolumes} />
                </>
            )}

            {currentView === 'approvals' && (
                <>
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <button onClick={() => handleSwitchView('list')} className="text-primary hover:text-teal-800 text-sm font-medium mb-3 flex items-center transition-colors">
                                <i className="fa-solid fa-arrow-left mr-2"></i> Quay lại danh sách
                            </button>
                            <h2 className="text-2xl font-bold text-slate-800">Phê duyệt yêu cầu mở khóa</h2>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <UnlockRequestTable requests={mockRequests} />
                    </div>
                </>
            )}
        </div>
    );
}
