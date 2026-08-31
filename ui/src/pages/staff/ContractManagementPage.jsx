import React, { useState, useEffect, useMemo } from 'react';
import StatCard from '../../components/production/StatCard';
import ContractTable from '../../components/contract/ContractTable';
import ContractForm from '../../components/contract/ContractForm';
import ContractDetailModal from '../../components/contract/ContractDetailModal';
import { 
    fetchContracts, 
    fetchCustomers, 
    createContract, 
    updateContract, 
    submitContract, 
    cancelContract,
    fetchContractDetail
} from '../../services/contractApi';

export default function ContractManagementStaffPage({ user }) {
    const [contracts, setContracts] = useState([]);
    const [customers, setCustomers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    const [statusFilter, setStatusFilter] = useState('');
    const [searchQuery, setSearchQuery] = useState('');

    const [showForm, setShowForm] = useState(false);
    const [editingContractId, setEditingContractId] = useState(null);
    
    const [detailData, setDetailData] = useState(null);
    const [showDetail, setShowDetail] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [contractsData, customersData] = await Promise.all([
                fetchContracts(),
                fetchCustomers()
            ]);
            setContracts(contractsData.items || []);
            setCustomers(customersData || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const stats = useMemo(() => {
        const total = contracts.length;
        const draft = contracts.filter(c => c.status === 'DRAFT').length;
        const submitted = contracts.filter(c => c.status === 'SUBMITTED').length;
        const underReview = contracts.filter(c => c.status === 'UNDER REVIEW').length;
        const approvedActive = contracts.filter(c => ['APPROVED', 'ACTIVE'].includes(c.status)).length;
        const rejectedCancelledExpired = contracts.filter(c => ['REJECTED', 'CANCELLED', 'EXPIRED'].includes(c.status)).length;

        return { total, draft, submitted, underReview, approvedActive, rejectedCancelledExpired };
    }, [contracts]);

    const filteredContracts = useMemo(() => {
        let result = contracts;
        if (statusFilter) {
            result = result.filter(c => c.status === statusFilter);
        }
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            result = result.filter(c => 
                c.contract_number.toLowerCase().includes(query) ||
                (customers.find(cust => cust.customer_id === c.customer_id)?.company_name || '').toLowerCase().includes(query)
            );
        }
        return result;
    }, [contracts, statusFilter, searchQuery, customers]);

    const handleCreateContract = async (payload) => {
        try {
            await createContract(payload);
            setShowForm(false);
            loadData();
        } catch (err) {
            alert('Lỗi khi tạo hợp đồng: ' + err.message);
        }
    };

    const handleUpdateContract = async (payload) => {
        try {
            // Need row_version to update. Let's fetch detail first or pass it from somewhere.
            // Since we edit, we probably fetched the detail. We need row_version!
            // Wait, for simplicity if we don't have row_version here, we fetch it first.
            const detail = await fetchContractDetail(editingContractId);
            payload.row_version = detail.row_version;

            await updateContract(editingContractId, payload);
            setEditingContractId(null);
            setShowForm(false);
            loadData();
        } catch (err) {
            alert('Lỗi khi cập nhật hợp đồng: ' + err.message);
        }
    };

    const handleSubmitContractForm = (payload) => {
        if (editingContractId) {
            handleUpdateContract(payload);
        } else {
            handleCreateContract(payload);
        }
    };

    const handleEditClick = async (contractId) => {
        try {
            const detail = await fetchContractDetail(contractId);
            setDetailData(detail);
            setEditingContractId(contractId);
            setShowForm(true);
        } catch (err) {
            alert('Không thể tải chi tiết hợp đồng để sửa: ' + err.message);
        }
    };

    const handleViewClick = async (contractId) => {
        try {
            const detail = await fetchContractDetail(contractId);
            setDetailData(detail);
            setShowDetail(true);
        } catch (err) {
            alert('Không thể tải chi tiết hợp đồng: ' + err.message);
        }
    };

    const handleSubmitClick = async (contractId) => {
        if (!confirm('Bạn có chắc chắn muốn submit hợp đồng này?')) return;
        try {
            const idempotencyKey = `submit-${contractId}-${Date.now()}`;
            await submitContract(contractId, idempotencyKey);
            loadData();
        } catch (err) {
            alert('Lỗi khi submit: ' + err.message);
        }
    };

    const handleCancelClick = async (contractId) => {
        const reason = prompt('Nhập lý do hủy:');
        if (!reason) return;
        try {
            await cancelContract(contractId, reason);
            loadData();
        } catch (err) {
            alert('Lỗi khi hủy: ' + err.message);
        }
    };

    return (
        <div className="p-8">
            <div className="flex justify-between items-start mb-8">
                <div>
                    <h2 className="text-2xl font-bold text-slate-800 mb-1">Quản lý hợp đồng</h2>
                    <p className="text-slate-500 text-sm">Quản lý vòng đời hợp đồng dịch vụ logistics.</p>
                </div>
                <div className="flex space-x-3">
                    <button 
                        onClick={() => {
                            setEditingContractId(null);
                            setShowForm(true);
                        }} 
                        className="bg-primary hover:bg-teal-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors flex items-center shadow-sm"
                    >
                        <i className="fa-solid fa-plus mr-2"></i> Tạo hợp đồng mới
                    </button>
                </div>
            </div>

            {error && (
                <div className="bg-red-50 text-red-600 p-4 rounded-lg mb-6 flex items-center">
                    <i className="fa-solid fa-circle-exclamation mr-2"></i> {error}
                </div>
            )}

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4 mb-8">
                <StatCard title="Tổng số hợp đồng" value={stats.total} icon="fa-solid fa-file-contract" colorClass="bg-slate-100 text-slate-500" />
                <StatCard title="DRAFT" value={stats.draft} icon="fa-solid fa-pen" colorClass="bg-yellow-50 text-yellow-500" />
                <StatCard title="SUBMITTED" value={stats.submitted} icon="fa-solid fa-hourglass-half" colorClass="bg-orange-50 text-orange-500" />
                <StatCard title="UNDER REVIEW" value={stats.underReview} icon="fa-solid fa-shield-halved" colorClass="bg-blue-50 text-blue-500" />
                <StatCard title="APPROVED / ACTIVE" value={stats.approvedActive} icon="fa-solid fa-check-double" colorClass="bg-green-50 text-green-500" />
                <StatCard title="CANCELED / EXPIRED" value={stats.rejectedCancelledExpired} icon="fa-solid fa-ban" colorClass="bg-red-50 text-red-500" />
            </div>

            {/* Filter Bar */}
            <div className="bg-white p-4 border border-slate-200 rounded-t-xl flex items-center justify-between shadow-sm">
                <div className="flex space-x-3">
                    <select 
                        value={statusFilter} 
                        onChange={(e) => setStatusFilter(e.target.value)}
                        className="border border-slate-300 rounded-md text-sm px-3 py-2 bg-white text-slate-700 outline-none focus:border-primary"
                    >
                        <option value="">Tất cả trạng thái</option>
                        <option value="DRAFT">DRAFT</option>
                        <option value="SUBMITTED">SUBMITTED</option>
                        <option value="UNDER REVIEW">UNDER REVIEW</option>
                        <option value="APPROVED">APPROVED</option>
                        <option value="ACTIVE">ACTIVE</option>
                        <option value="REJECTED">REJECTED</option>
                        <option value="CANCELLED">CANCELLED</option>
                        <option value="EXPIRED">EXPIRED</option>
                    </select>
                </div>
                <div className="flex items-center space-x-3">
                    <div className="relative w-64">
                        <i className="fa-solid fa-search absolute left-3 top-2.5 text-slate-400 text-sm"></i>
                        <input 
                            type="text" 
                            placeholder="Tìm kiếm số HĐ, Tên KH..." 
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full border border-slate-300 rounded-md pl-9 pr-3 py-2 text-sm outline-none focus:border-primary bg-white" 
                        />
                    </div>
                </div>
            </div>

            {isLoading ? (
                <div className="bg-white p-10 text-center text-slate-500 rounded-b-xl border border-t-0 border-slate-200">
                    <i className="fa-solid fa-circle-notch fa-spin text-2xl mb-2"></i>
                    <p>Đang tải dữ liệu...</p>
                </div>
            ) : (
                <ContractTable 
                    contracts={filteredContracts} 
                    customers={customers}
                    onView={handleViewClick}
                    onEdit={handleEditClick}
                    onSubmit={handleSubmitClick}
                    onCancel={handleCancelClick}
                />
            )}

            {showForm && (
                <ContractForm 
                    initialData={editingContractId ? detailData?.current_version_detail : null}
                    customers={customers}
                    onClose={() => setShowForm(false)}
                    onSubmit={handleSubmitContractForm}
                />
            )}

            {showDetail && (
                <ContractDetailModal 
                    detail={detailData}
                    customers={customers}
                    onClose={() => setShowDetail(false)}
                />
            )}
        </div>
    );
}
