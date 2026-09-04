import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Ban, CheckCircle2, FileText, Plus, RefreshCcw, Send, ShieldCheck } from 'lucide-react';
import ContractTable from '../../components/contract/ContractTable';
import ContractForm from '../../components/contract/ContractForm';
import ContractDetailModal from '../../components/contract/ContractDetailModal';
import ContractConfirmationModal from '../../components/contract/ContractConfirmationModal';
import { useToast } from '../../components/common/ToastContext';
import {
    cancelContract,
    createContract,
    fetchContractDetail,
    fetchContracts,
    fetchCustomers,
    getContractErrorMessage,
    submitContract,
    updateContract,
} from '../../services/contractApi';

const PAGE_SIZE = 10;
const STATUS_OPTIONS = [
    'DRAFT',
    'SUBMITTED',
    'MANAGER_REVIEW',
    'DIRECTOR_REVIEW',
    'REVISION_REQUESTED',
    'APPROVED',
    'ACTIVE',
    'EXPIRED',
    'REJECTED',
    'CANCELLED',
];

const count = (summary, status) => summary[status.toLowerCase()] || 0;

export default function ContractManagementStaffPage() {
    const toast = useToast();
    const [contracts, setContracts] = useState([]);
    const [customers, setCustomers] = useState([]);
    const [summary, setSummary] = useState({});
    const [totalContracts, setTotalContracts] = useState(0);
    const [page, setPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [showForm, setShowForm] = useState(false);
    const [editingContractId, setEditingContractId] = useState(null);
    const [detailData, setDetailData] = useState(null);
    const [showDetail, setShowDetail] = useState(false);
    const [confirmation, setConfirmation] = useState(null);

    const loadData = useCallback(async () => {
        setIsLoading(true);
        try {
            const [contractsData, customersData] = await Promise.all([
                fetchContracts({
                    skip: (page - 1) * PAGE_SIZE,
                    limit: PAGE_SIZE,
                    status: statusFilter,
                    search: searchQuery,
                }),
                fetchCustomers(),
            ]);
            const responseTotal = contractsData.total || 0;
            const lastPage = Math.max(1, Math.ceil(responseTotal / PAGE_SIZE));

            setContracts(contractsData.items || []);
            setTotalContracts(responseTotal);
            setSummary(contractsData.summary || {});
            setCustomers(customersData || []);
            setError('');

            if (page > lastPage) setPage(lastPage);
        } catch (loadError) {
            setError(getContractErrorMessage(loadError, 'Không thể tải dữ liệu hợp đồng.'));
        } finally {
            setIsLoading(false);
        }
    }, [page, searchQuery, statusFilter]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const stats = useMemo(() => {
        const statuses = Object.fromEntries(STATUS_OPTIONS.map((status) => [status, count(summary, status)]));
        const lifecycleTotal = Object.values(statuses).reduce((total, value) => total + value, 0);
        return { ...statuses, total: summary.total ?? lifecycleTotal };
    }, [summary]);

    const kpiGroups = [
        {
            title: 'Soạn thảo & gửi duyệt',
            icon: <Send size={18} />,
            tone: 'blue',
            items: [['DRAFT', stats.DRAFT], ['SUBMITTED', stats.SUBMITTED]],
        },
        {
            title: 'Đang phê duyệt',
            icon: <ShieldCheck size={18} />,
            tone: 'purple',
            items: [['MANAGER_REVIEW', stats.MANAGER_REVIEW], ['DIRECTOR_REVIEW', stats.DIRECTOR_REVIEW]],
        },
        {
            title: 'Cần xử lý',
            icon: <RefreshCcw size={18} />,
            tone: 'orange',
            items: [['REVISION_REQUESTED', stats.REVISION_REQUESTED], ['REJECTED', stats.REJECTED], ['CANCELLED', stats.CANCELLED]],
        },
        {
            title: 'Đã hoàn tất',
            icon: <CheckCircle2 size={18} />,
            tone: 'green',
            items: [['APPROVED', stats.APPROVED], ['ACTIVE', stats.ACTIVE], ['EXPIRED', stats.EXPIRED]],
        },
    ];

    const handleCreateContract = async (payload) => {
        try {
            const { attachments = [], ...contractData } = payload;
            await createContract(contractData, attachments);
            toast.success('Tạo hợp đồng thành công.');
            setShowForm(false);
            await loadData();
        } catch (actionError) {
            toast.error(getContractErrorMessage(actionError, 'Không thể tạo hợp đồng.'));
        }
    };

    const handleUpdateContract = async (payload) => {
        try {
            const { attachments = [], ...contractData } = payload;
            const detail = await fetchContractDetail(editingContractId);
            await updateContract(editingContractId, { ...contractData, row_version: detail.row_version }, attachments);
            toast.success('Cập nhật hợp đồng thành công.');
            setEditingContractId(null);
            setShowForm(false);
            await loadData();
        } catch (actionError) {
            toast.error(getContractErrorMessage(actionError, 'Không thể cập nhật hợp đồng.'));
        }
    };

    const handleSubmitContractForm = (payload) => editingContractId
        ? handleUpdateContract(payload)
        : handleCreateContract(payload);

    const handleEditClick = async (contractId) => {
        try {
            const detail = await fetchContractDetail(contractId);
            setDetailData(detail);
            setEditingContractId(contractId);
            setShowForm(true);
        } catch (viewError) {
            toast.error(getContractErrorMessage(viewError, 'Không thể tải chi tiết hợp đồng để sửa.'));
        }
    };

    const handleViewClick = async (contractId) => {
        try {
            setDetailData(await fetchContractDetail(contractId));
            setShowDetail(true);
        } catch (viewError) {
            toast.error(getContractErrorMessage(viewError, 'Không thể tải chi tiết hợp đồng.'));
        }
    };

    const handleSubmitClick = (contractId) => {
        const contract = contracts.find((item) => item.contract_id === contractId);
        setConfirmation({ type: 'submit', contractId, contractNumber: contract?.contract_number || contractId });
    };

    const handleCancelClick = (contractId) => {
        const contract = contracts.find((item) => item.contract_id === contractId);
        setConfirmation({ type: 'cancel', contractId, contractNumber: contract?.contract_number || contractId });
    };

    const handleConfirmAction = async (reason) => {
        try {
            if (confirmation.type === 'submit') {
                await submitContract(confirmation.contractId, `submit-${confirmation.contractId}-${Date.now()}`);
                toast.success('Gửi hợp đồng để duyệt thành công.');
            } else {
                await cancelContract(confirmation.contractId, reason);
                toast.success('Hủy hợp đồng thành công.');
            }
            await loadData();
            return true;
        } catch (actionError) {
            const fallback = confirmation.type === 'submit'
                ? 'Không thể gửi hợp đồng để duyệt.'
                : 'Không thể hủy hợp đồng.';
            toast.error(getContractErrorMessage(actionError, fallback));
            return false;
        }
    };

    const totalPages = Math.max(1, Math.ceil(totalContracts / PAGE_SIZE));

    return (
        <div className="manager-contract-page staff-contract-page">
            <div className="manager-page-heading">
                <div>
                    <h1>Quản lý hợp đồng (Staff)</h1>
                    <p>Quản lý vòng đời hợp đồng dịch vụ logistics.</p>
                </div>
                <button
                    type="button"
                    className="staff-create-contract"
                    onClick={() => {
                        setEditingContractId(null);
                        setDetailData(null);
                        setShowForm(true);
                    }}
                >
                    <Plus size={17} /> Tạo hợp đồng mới
                </button>
            </div>

            <div className="staff-contract-summary">
                <div className="staff-total-card">
                    <span className="staff-summary-icon"><FileText size={21} /></span>
                    <div><p>Tổng hợp đồng</p><strong>{stats.total}</strong><small>Toàn bộ trạng thái</small></div>
                </div>
                {kpiGroups.map((group) => (
                    <section className={`staff-kpi-group staff-kpi-${group.tone}`} key={group.title}>
                        <header><span>{group.icon}</span><h2>{group.title}</h2></header>
                        <div className="staff-kpi-values">
                            {group.items.map(([status, value]) => (
                                <div key={status}><span>{status}</span><strong>{value}</strong></div>
                            ))}
                        </div>
                    </section>
                ))}
            </div>

            <section className="manager-contract-panel">
                <div className="manager-panel-title"><h2>Danh sách hợp đồng</h2></div>
                <div className="manager-filter-bar">
                    <div className="manager-select-wrap">
                        <select value={statusFilter} onChange={(event) => { setPage(1); setStatusFilter(event.target.value); }}>
                            <option value="">Trạng thái: Tất cả</option>
                            {STATUS_OPTIONS.map((status) => <option key={status} value={status}>{status}</option>)}
                        </select>
                    </div>
                    <div className="manager-search-wrap">
                        <i className="fa-solid fa-search" />
                        <input value={searchQuery} onChange={(event) => { setPage(1); setSearchQuery(event.target.value); }} placeholder="Tìm kiếm số HĐ, tên khách hàng..." />
                    </div>
                    <button className="manager-filter-button" type="button" title="Xóa bộ lọc" onClick={() => { setPage(1); setStatusFilter(''); setSearchQuery(''); }}>
                        <Ban size={15} />
                    </button>
                </div>

                {error && <div className="manager-error">{error}</div>}
                {isLoading ? (
                    <div className="manager-loading">Đang tải dữ liệu hợp đồng...</div>
                ) : (
                    <ContractTable
                        contracts={contracts}
                        customers={customers}
                        totalCount={totalContracts}
                        page={page}
                        pageSize={PAGE_SIZE}
                        totalPages={totalPages}
                        onPageChange={setPage}
                        onView={handleViewClick}
                        onEdit={handleEditClick}
                        onSubmit={handleSubmitClick}
                        onCancel={handleCancelClick}
                    />
                )}
            </section>

            {showForm && (
                <ContractForm
                    initialData={editingContractId ? detailData?.current_version_detail : null}
                    customers={customers}
                    onClose={() => setShowForm(false)}
                    onSubmit={handleSubmitContractForm}
                    contractStatus={detailData?.status || ''}
                    existingAttachments={detailData?.attachments || []}
                />
            )}
            {showDetail && (
                <ContractDetailModal detail={detailData} customers={customers} viewerRole="STAFF" onClose={() => setShowDetail(false)} />
            )}
            {confirmation && (
                <ContractConfirmationModal
                    type={confirmation.type}
                    contractNumber={confirmation.contractNumber}
                    onClose={() => setConfirmation(null)}
                    onConfirm={handleConfirmAction}
                />
            )}
        </div>
    );
}
