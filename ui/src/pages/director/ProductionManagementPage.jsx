import React, { useState, useEffect } from 'react';
import StatCard from '../../components/production/StatCard';
import VolumeTable from '../../components/production/VolumeTable';
import UnlockRequestTable from '../../components/production/UnlockRequestTable';

export default function ProductionManagementDirectorPage({ user }) {
    const [currentView, setCurrentView] = useState('list'); // 'list' | 'approvals'

    const [volumes, setVolumes] = useState([]);
    const [requests, setRequests] = useState([]);
    const [periods, setPeriods] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchData = async () => {
        setLoading(true);
        try {
            const token = localStorage.getItem('token') || '';
            const headers = { 'Authorization': `Bearer ${token}` };
            
            const [volumesRes, requestsRes, periodsRes] = await Promise.all([
                fetch('http://localhost:8084/api/v1/volumes', { headers }),
                fetch('http://localhost:8084/api/v1/periods/unlock-requests', { headers }),
                fetch('http://localhost:8084/api/v1/periods', { headers })
            ]);
            
            if (volumesRes.ok) {
                setVolumes(await volumesRes.json());
            }
            if (requestsRes.ok) {
                setRequests(await requestsRes.json());
            }
            if (periodsRes.ok) {
                setPeriods(await periodsRes.json());
            }
        } catch (error) {
            console.error("Error fetching data", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [currentView]);

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
                                <i className="fa-solid fa-bell mr-2"></i> Phê duyệt yêu cầu ({requests.filter(r => r.status === 'PENDING').length})
                            </button>
                        </div>
                    </div>

                    {/* Summary Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                        <StatCard title="Tổng bản ghi" value={volumes.length} icon="fa-regular fa-folder" colorClass="bg-slate-100 text-slate-500" />
                        <StatCard title="Kỳ chưa khóa" value={periods.filter(p => p.status === 'OPEN').length} icon="fa-solid fa-lock-open" colorClass="bg-amber-50 text-amber-500" />
                        <StatCard title="Kỳ đã khóa" value={periods.filter(p => p.status === 'LOCKED').length} icon="fa-solid fa-lock" colorClass="bg-red-50 text-red-500" />
                        <StatCard title="Yêu cầu chờ duyệt" value={requests.filter(r => r.status === 'PENDING').length} icon="fa-solid fa-bell" colorClass="bg-amber-50 text-amber-500" />
                    </div>

                    {/* Table */}
                    <VolumeTable volumes={volumes} onRefresh={fetchData} />
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
                    <div className="w-full">
                        <UnlockRequestTable requests={requests} onRefresh={fetchData} />
                    </div>
                </>
            )}
        </div>
    );
}
