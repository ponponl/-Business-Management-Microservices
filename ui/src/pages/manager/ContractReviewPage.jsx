import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ClipboardCheck, Eye, FileCheck2, History, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ContractDetailModal from '../../components/contract/ContractDetailModal';
import ContractProcessingModal from '../../components/contract/ContractProcessingModal';
import { useToast } from '../../components/common/ToastContext';
import { fetchContractDetail, fetchContracts, fetchCustomers, getContractErrorMessage, startContractReview } from '../../services/contractApi';

const REVIEW_STATUSES = new Set(['SUBMITTED', 'MANAGER_REVIEW']);
const TABS = [
    { value: '', label: 'Tất cả' },
    { value: 'SUBMITTED', label: 'Submitted' },
    { value: 'MANAGER_REVIEW', label: 'Manager Review' },
];

const formatMoney = (value) => value === null || value === undefined
    ? 'N/A'
    : new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);

const formatDate = (value) => {
    if (!value) return 'N/A';
    const dateOnly = String(value).split('T')[0];
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateOnly);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : 'N/A';
};

const formatDateRange = (from, to) => {
    if (!from && !to) return 'N/A';
    if (!from || !to) return formatDate(from || to);
    return `${formatDate(from)} - ${formatDate(to)}`;
};

function StatusBadge({ status }) {
    const isReview = status === 'MANAGER_REVIEW';
    return <span className={`review-status-badge ${isReview ? 'is-review' : 'is-submitted'}`}>{isReview ? 'MANAGER_REVIEW' : 'SUBMITTED'}</span>;
}

export default function ContractReviewPage() {
    const navigate = useNavigate();
    const toast = useToast();
    const [contracts, setContracts] = useState([]);
    const [summary, setSummary] = useState({});
    const [customers, setCustomers] = useState([]);
    const [activeTab, setActiveTab] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [loading, setLoading] = useState(true);
    const [processingId, setProcessingId] = useState(null);
    const [error, setError] = useState('');
    const [detail, setDetail] = useState(null);
    const [processingContract, setProcessingContract] = useState(null);

    const loadData = async () => {
        setLoading(true);
        try {
            const [submittedResponse, reviewResponse, customerResponse] = await Promise.all([
                fetchContracts({ status: 'SUBMITTED', limit: 100 }),
                fetchContracts({ status: 'MANAGER_REVIEW', limit: 100 }),
                fetchCustomers(),
            ]);
            setContracts([
                ...(submittedResponse.items || []),
                ...(reviewResponse.items || []),
            ].filter((contract) => REVIEW_STATUSES.has(contract.status)));
            setSummary(submittedResponse.summary || reviewResponse.summary || {});
            setCustomers(customerResponse || []);
            setError('');
        } catch (loadError) {
            setError(loadError.message || 'Không thể tải danh sách cần duyệt.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    const customerName = (customerId) => customers.find((customer) => customer.customer_id === customerId)?.company_name || customerId;
    const filteredContracts = useMemo(() => contracts.filter((contract) => {
        const query = searchQuery.trim().toLowerCase();
        const matchesTab = !activeTab || contract.status === activeTab;
        const matchesSearch = !query || contract.contract_number.toLowerCase().includes(query) || customerName(contract.customer_id).toLowerCase().includes(query);
        return matchesTab && matchesSearch;
    }), [contracts, customers, activeTab, searchQuery]);

    const handleStartReview = async (contractId) => {
        setProcessingId(contractId);
        try {
            const result = await startContractReview(contractId);
            setContracts((current) => current.map((contract) => contract.contract_id === contractId
                ? { ...contract, status: result.status || 'MANAGER_REVIEW' }
                : contract));
            setSummary((current) => ({
                ...current,
                submitted: Math.max(0, (current.submitted || 0) - 1),
                manager_review: (current.manager_review || 0) + 1,
            }));
            toast.success('Đã bắt đầu review hợp đồng.');
        } catch (actionError) {
            toast.error(getContractErrorMessage(actionError, 'Không thể bắt đầu review hợp đồng.'));
        } finally {
            setProcessingId(null);
        }
    };

    const handleView = async (contractId) => {
        try { setDetail(await fetchContractDetail(contractId)); }
        catch (viewError) { toast.error(getContractErrorMessage(viewError, 'Không thể tải chi tiết hợp đồng.')); }
    };

    const handleProcessingSuccess = async () => {
        setProcessingContract(null);
        await loadData();
    };

    return <div className="contract-review-page">
        <button className="review-back-link" type="button" onClick={() => navigate('/manager/contracts')}><ArrowLeft size={15} /> Quay lại danh sách hợp đồng</button>
        <div className="review-heading"><h1>Duyệt hợp đồng</h1><p>Theo dõi và xử lý các hợp đồng đang chờ Manager duyệt</p></div>

        <div className="review-kpi-grid">
            <KpiCard label="Tổng cần duyệt" value={(summary.submitted || 0) + (summary.manager_review || 0)} icon={<FileCheck2 />} tone="green" />
            <KpiCard label="Đang review" value={summary.manager_review || 0} icon={<History />} tone="purple" />
        </div>

        <section className="review-panel">
            <div className="review-panel-heading"><h2>Danh sách hợp đồng cần duyệt</h2><p>Danh sách chỉ hiển thị các contract cần theo dõi nhanh, thông tin chi tiết xem tại biểu tượng con mắt.</p></div>
            <div className="review-toolbar"><div className="review-tabs">{TABS.map((tab) => <button key={tab.value} type="button" className={activeTab === tab.value ? 'active' : ''} onClick={() => setActiveTab(tab.value)}>{tab.label}</button>)}</div><label className="review-search"><Search size={16} /><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Tìm kiếm mã HĐ, khách hàng..." /></label></div>
            {error && <div className="review-error">{error}</div>}
            <div className="review-table-wrap"><table className="review-table"><thead><tr><th>Mã HĐ</th><th>Khách hàng</th><th>Giá trị hợp đồng</th><th>Thời gian hiệu lực</th><th>Trạng thái</th><th>Xem chi tiết</th><th>Thao tác</th></tr></thead><tbody>{loading ? <tr><td colSpan="7" className="review-empty">Đang tải dữ liệu...</td></tr> : filteredContracts.length === 0 ? <tr><td colSpan="7" className="review-empty"><ClipboardCheck size={72} /><strong>Không còn hợp đồng cần duyệt</strong><span>Tất cả hợp đồng đã được Manager xử lý hoặc đã chuyển sang bước tiếp theo.</span></td></tr> : filteredContracts.map((contract) => <tr key={contract.contract_id}><td className="contract-number">{contract.contract_number}</td><td>{customerName(contract.customer_id)}</td><td>{formatMoney(contract.contract_value)}</td><td>{formatDateRange(contract.effective_from, contract.effective_to)}</td><td><StatusBadge status={contract.status} /></td><td><button className="review-icon-button" type="button" title="Xem chi tiết" onClick={() => handleView(contract.contract_id)}><Eye size={16} /></button></td><td>{contract.status === 'SUBMITTED' ? <button className="review-action-button start" type="button" disabled={processingId === contract.contract_id} onClick={() => handleStartReview(contract.contract_id)}>{processingId === contract.contract_id ? 'Đang xử lý...' : 'Bắt đầu review'}</button> : <button className="review-action-button continue" type="button" onClick={() => setProcessingContract(contract)}>Review</button>}</td></tr>)}</tbody></table></div>
            <div className="review-footer"><span>Hiển thị 1 - {filteredContracts.length} của {filteredContracts.length} hợp đồng</span><div><button type="button" disabled>‹</button><button type="button" className="current">1</button><button type="button" disabled>›</button></div></div>
        </section>
        {detail && <ContractDetailModal detail={detail} customers={customers} viewerRole="MANAGER" onClose={() => setDetail(null)} />}
        {processingContract && <ContractProcessingModal contract={processingContract} customerName={customerName(processingContract.customer_id)} onClose={() => setProcessingContract(null)} onSuccess={handleProcessingSuccess} />}
    </div>;
}

function KpiCard({ label, value, icon, tone }) {
    return <div className="review-kpi-card"><div><p>{label}</p><strong>{value}</strong></div><span className={`review-kpi-icon ${tone}`}>{icon}</span></div>;
}
