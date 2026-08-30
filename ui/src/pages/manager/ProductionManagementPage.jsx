import React, { useState } from 'react';
import StatCard from '../../components/production/StatCard';
import VolumeTable from '../../components/production/VolumeTable';
import PeriodTable from '../../components/production/PeriodTable';

export default function ProductionManagementManagerPage({ user }) {
    const [currentView, setCurrentView] = useState('list'); // 'list' | 'periods'

    // Mock data for initial UI check
    const mockVolumes = [
        { id: 'VOL-1001', contractId: 'HD-2024-001', date: '2026-08-25', serviceName: 'Bốc xếp container 20ft (Hàng nhập)', quantity: 50, unit: 'Container', status: 'LOCKED', handler: 'Nguyễn Văn A' },
        { id: 'VOL-1002', contractId: 'HD-2024-002', date: '2026-08-26', serviceName: 'Lưu kho bãi tổng hợp', quantity: 120.5, unit: 'Ngày/Tấn', status: 'UNLOCKED', handler: 'Nguyễn Văn B' },
        { id: 'VOL-1003', contractId: 'HD-2024-003', date: '2026-08-26', serviceName: 'Khai thác bến bãi hạ tải', quantity: 15, unit: 'Lượt xe', status: 'PENDING', handler: 'Nguyễn Văn B' }
    ];

    const mockPeriods = [
        { id: 'P07', month: '07/2026', status: 'LOCKED' },
        { id: 'P08', month: '08/2026', status: 'UNLOCKED' }
    ];

    const handleSwitchView = (view) => setCurrentView(view);

    return (
        <div className="p-8">
            {currentView === 'list' && (
                <>
                    {/* Page Title */}
                    <div className="flex justify-between items-start mb-8">
                        <div>
                            <h2 className="text-2xl font-bold text-slate-800 mb-1">Quản lý sản lượng (Manager)</h2>
                            <p className="text-slate-500 text-sm">Quản lý chung, theo dõi và chốt kỳ sản lượng.</p>
                        </div>
                        <div className="flex space-x-3">
                            <button onClick={() => handleSwitchView('periods')} className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center shadow-sm">
                                <i className="fa-solid fa-lock mr-2"></i> Kỳ vận hành & Chốt sổ
                            </button>
                        </div>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <StatCard title="Tổng bản ghi" value="2" icon="fa-regular fa-folder" colorClass="bg-slate-100 text-slate-500" />
                        <StatCard title="Sản lượng Container" value="50" icon="fa-solid fa-box" colorClass="bg-amber-50 text-amber-500" />
                        <StatCard title="Sản lượng Hàng rời" value="120.5" icon="fa-solid fa-weight-hanging" colorClass="bg-green-50 text-green-500" />
                        <StatCard title="Kỳ đã khóa" value="1" icon="fa-solid fa-lock" colorClass="bg-red-50 text-red-500" />
                    </div>

                    {/* Table */}
                    <VolumeTable volumes={mockVolumes} />
                </>
            )}

            {currentView === 'periods' && (
                <>
                    <div className="flex justify-between items-center mb-6">
                        <div>
                            <button onClick={() => handleSwitchView('list')} className="text-primary hover:text-teal-800 text-sm font-medium mb-3 flex items-center transition-colors">
                                <i className="fa-solid fa-arrow-left mr-2"></i> Quay lại danh sách
                            </button>
                            <h2 className="text-2xl font-bold text-slate-800">Quản lý kỳ vận hành</h2>
                        </div>
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <PeriodTable periods={mockPeriods} />
                    </div>
                </>
            )}
        </div>
    );
}
