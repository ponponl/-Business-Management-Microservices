import React, { useState } from 'react';
import StatCard from '../../components/production/StatCard';
import VolumeTable from '../../components/production/VolumeTable';
import RecordVolumeForm from '../../components/production/RecordVolumeForm';

export default function ProductionManagementStaffPage({ user }) {
    const [currentView, setCurrentView] = useState('list'); // 'list' | 'record'

    // Mock data for initial UI check
    const mockVolumes = [
        { id: 'VOL-1001', customerName: 'Công ty XNK Bình Dương', date: '2026-08-25', serviceName: 'Bốc xếp container 20ft (Hàng nhập)', quantity: 50, unit: 'Container', status: 'LOCKED', handler: 'Nguyễn Văn A' },
        { id: 'VOL-1002', customerName: 'Công ty Thủy Hải Sản ĐN', date: '2026-08-26', serviceName: 'Lưu kho bãi tổng hợp', quantity: 120.5, unit: 'Ngày/Tấn', status: 'UNLOCKED', handler: 'Nguyễn Văn B' },
        { id: 'VOL-1003', customerName: 'Tập đoàn ABC', date: '2026-08-26', serviceName: 'Khai thác bến bãi hạ tải', quantity: 15, unit: 'Lượt xe', status: 'DRAFT', handler: 'Nguyễn Văn B' }
    ];

    const handleSwitchView = (view) => setCurrentView(view);

    return (
        <div className="p-8">
            {currentView === 'list' && (
                <>
                    {/* Page Title */}
                    <div className="flex justify-between items-start mb-8">
                        <div>
                            <h2 className="text-2xl font-bold text-slate-800 mb-1">Quản lý sản lượng</h2>
                            <p className="text-slate-500 text-sm">Ghi nhận, đối soát và xin mở khóa kỳ số liệu khai thác.</p>
                        </div>
                        <div className="flex space-x-3">
                            <button onClick={() => handleSwitchView('record')} className="bg-primary hover:bg-teal-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center shadow-sm">
                                <i className="fa-solid fa-plus mr-2"></i> Ghi nhận sản lượng
                            </button>
                        </div>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <StatCard title="Tổng bản ghi" value="3" icon="fa-regular fa-folder" colorClass="bg-slate-100 text-slate-500" />
                        <StatCard title="Sản lượng Container" value="50" icon="fa-solid fa-box" colorClass="bg-amber-50 text-amber-500" />
                        <StatCard title="Sản lượng Hàng rời" value="120.5" icon="fa-solid fa-weight-hanging" colorClass="bg-green-50 text-green-500" />
                        <StatCard title="Kỳ đã khóa" value="1" icon="fa-solid fa-lock" colorClass="bg-red-50 text-red-500" />
                    </div>

                    {/* Table */}
                    <VolumeTable volumes={mockVolumes} />
                </>
            )}

            {currentView === 'record' && (
                <RecordVolumeForm 
                    onCancel={() => handleSwitchView('list')} 
                    onSubmit={() => handleSwitchView('list')} 
                />
            )}
        </div>
    );
}
