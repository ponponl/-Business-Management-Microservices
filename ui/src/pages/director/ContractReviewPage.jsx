import React, { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ClipboardCheck, Eye, FileCheck2, History, Search } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ContractDetailModal from '../../components/contract/ContractDetailModal';
import ContractProcessingModal from '../../components/contract/ContractProcessingModal';
import { fetchContractDetail, fetchContracts, fetchCustomers, startContractReview } from '../../services/contractApi';

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

export default function ContractReviewDirectorPage() {
    const navigate = useNavigate();
    const [contracts, setContracts] = useState([]);
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
            const [contractResponse, customerResponse] = await Promise.all([
                fetchContracts({ status: 'DIRECTOR_REVIEW', limit: 100 }),
                fetchCustomers(),
            ]);
            setContracts((contractResponse.items || []).filter((contract) => contract.status === 'DIRECTOR_REVIEW'));
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
        const matchesTab = !activeTab || activeTab === contract.status;
        const matchesSearch = !query || contract.contract_number.toLowerCase().includes(query) || customerName(contract.customer_id).toLowerCase().includes(query);
        return matchesTab && matchesSearch;
    }), [contracts, customers, activeTab, searchQuery]);

    const handleStartReview = async (contract) => {
        setProcessingId(contract.contract_id);
        try {
            const response = await startContractReview(contract.contract_id);
            setProcessingContract({ ...contract, status: response.status || 'DIRECTOR_REVIEW' });
        } catch (actionError) {
            alert(`Không thể bắt đầu review: ${actionError.message}`);
        } finally {
            setProcessingId(null);
        }
    };

    const handleView = async (contractId) => {
        try { setDetail(await fetchContractDetail(contractId)); }
        catch (viewError) { alert(`Không thể tải chi tiết hợp đồng: ${viewError.message}`); }
    };

    const handleProcessingSuccess = async () => {
        setProcessingContract(null);
        await loadData();
    };

    return <div className="contract-review-page">
        <button className="review-back-link" type="button" onClick={() => navigate('/director/contracts')}><ArrowLeft size={15} /> Quay lại danh sách hợp đồng</button>
        <div className="review-heading"><h1>Duyệt hợp đồng</h1><p>Theo dõi và xử lý các hợp đồng đang chờ Director duyệt</p></div>
        <div className="review-kpi-grid"><KpiCard label="Tổng cần duyệt" value={contracts.length} icon={<FileCheck2 />} tone="green" /><KpiCard label="Đang review" value={contracts.length} icon={<History />} tone="purple" /></div>
        <section className="review-panel">
            <div className="review-panel-heading"><h2>Danh sách hợp đồng cần duyệt</h2><p>Danh sách chỉ hiển thị các contract cần theo dõi nhanh, thông tin chi tiết xem tại biểu tượng con mắt.</p></div>
            <div className="review-toolbar"><div className="review-tabs"><button type="button" className={activeTab === '' ? 'active' : ''} onClick={() => setActiveTab('')}>Tất cả</button><button type="button" className={activeTab === 'DIRECTOR_REVIEW' ? 'active' : ''} onClick={() => setActiveTab('DIRECTOR_REVIEW')}>Director Review</button></div><label className="review-search"><Search size={16} /><input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Tìm kiếm mã HĐ, khách hàng..." /></label></div>
            {error && <div className="review-error">{error}</div>}
            <div className="review-table-wrap"><table className="review-table"><thead><tr><th>Mã HĐ</th><th>Khách hàng</th><th>Giá trị hợp đồng</th><th>Thời gian hiệu lực</th><th>Trạng thái</th><th>Xem chi tiết</th><th>Thao tác</th></tr></thead><tbody>{loading ? <tr><td colSpan="7" className="review-empty">Đang tải dữ liệu...</td></tr> : filteredContracts.length === 0 ? <tr><td colSpan="7" className="review-empty"><ClipboardCheck size={72} /><strong>Không còn hợp đồng cần duyệt</strong><span>Tất cả hợp đồng đã được Director xử lý hoặc đã chuyển sang bước tiếp theo.</span></td></tr> : filteredContracts.map((contract) => <tr key={contract.contract_id}><td className="contract-number">{contract.contract_number}</td><td>{customerName(contract.customer_id)}</td><td>{formatMoney(contract.contract_value)}</td><td>{formatDateRange(contract.effective_from, contract.effective_to)}</td><td><span className="review-status-badge is-review">DIRECTOR_REVIEW</span></td><td><button className="review-icon-button" type="button" title="Xem chi tiết" onClick={() => handleView(contract.contract_id)}><Eye size={16} /></button></td><td><button className="review-action-button start" type="button" disabled={processingId === contract.contract_id} onClick={() => handleStartReview(contract)}>{processingId === contract.contract_id ? 'Đang xử lý...' : 'Bắt đầu Review'}</button></td></tr>)}</tbody></table></div>
            <div className="review-footer"><span>Hiển thị 1 - {filteredContracts.length} của {filteredContracts.length} hợp đồng</span><div><button type="button" disabled>‹</button><button type="button" className="current">1</button><button type="button" disabled>›</button></div></div>
        </section>
        {detail && <ContractDetailModal detail={detail} customers={customers} onClose={() => setDetail(null)} />}
        {processingContract && <ContractProcessingModal contract={processingContract} customerName={customerName(processingContract.customer_id)} role="DIRECTOR" onClose={() => setProcessingContract(null)} onSuccess={handleProcessingSuccess} />}
    </div>;
}

function KpiCard({ label, value, icon, tone }) {
    return <div className="review-kpi-card"><div><p>{label}</p><strong>{value}</strong></div><span className={`review-kpi-icon ${tone}`}>{icon}</span></div>;
}
