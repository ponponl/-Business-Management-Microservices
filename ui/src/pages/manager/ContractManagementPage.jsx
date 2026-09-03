import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, SlidersHorizontal, CalendarDays, CheckSquare, CheckCircle2, Pencil, XCircle, Clock3, Users } from 'lucide-react';
import ContractTable from '../../components/contract/ContractTable';
import ContractDetailModal from '../../components/contract/ContractDetailModal';
import { fetchContractDetail, fetchContracts, fetchCustomers } from '../../services/contractApi';

const statusOptions = [
    ['APPROVED', 'Đã Approved'],
    ['ACTIVE', 'Đã Active'],
    ['REVISION_REQUESTED', 'Cần Revision'],
    ['REJECTED', 'Đã Reject'],
    ['EXPIRED', 'Đã Expired'],
    ['DIRECTOR_REVIEW', 'Director Review'],
];

const managerStatuses = new Set(statusOptions.map(([status]) => status));

export default function ContractManagementManagerPage() {
    const navigate = useNavigate();
    const PAGE_SIZE = 10;
    const [contracts, setContracts] = useState([]);
    const [totalContracts, setTotalContracts] = useState(0);
    const [summary, setSummary] = useState({});
    const [page, setPage] = useState(1);
    const [customers, setCustomers] = useState([]);
    const [statusFilter, setStatusFilter] = useState('');
    const [searchQuery, setSearchQuery] = useState('');
    const [dateQuery, setDateQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [detailData, setDetailData] = useState(null);

    const loadData = async () => {
        setIsLoading(true);
        try {
            const [contractsData, customersData] = await Promise.all([
                fetchContracts({ skip: (page - 1) * PAGE_SIZE, limit: PAGE_SIZE, status: statusFilter, search: searchQuery, effectiveDate: dateQuery }),
                fetchCustomers(),
            ]);
            setContracts(contractsData.items || []);
            setTotalContracts(contractsData.total || 0);
            setSummary(contractsData.summary || {});
            setCustomers(customersData || []);
            setError('');
        } catch (err) {
            setError(err.message || 'Không thể tải dữ liệu hợp đồng.');
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => { loadData(); }, [page, statusFilter, searchQuery, dateQuery]);

    const stats = useMemo(() => ({
        approved: summary.approved || 0,
        active: summary.active || 0,
        revision: summary.revision_requested_by_manager || 0,
        rejected: summary.rejected || 0,
        expired: summary.expired || 0,
        review: summary.director_review || 0,
    }), [summary]);

    const viewContract = async (contractId) => {
        try { setDetailData(await fetchContractDetail(contractId)); }
        catch (err) { alert(`Không thể tải chi tiết hợp đồng: ${err.message}`); }
    };

    return (
        <div className="manager-contract-page">
            <div className="manager-page-heading">
                <div>
                    <p className="manager-eyebrow">Nghiệp vụ / Trang chủ</p>
                    <h1>Quản lý hợp đồng (Manager)</h1>
                    <p>Theo dõi tình trạng hợp đồng và duyệt các hợp đồng cần xử lý.</p>
                </div>
                <button className="manager-primary-action" type="button" onClick={() => navigate('/manager/contracts/review')}>
                    <CheckSquare size={17} /> Duyệt hợp đồng <span>{stats.review}</span>
                </button>
            </div>

            <div className="manager-stat-grid">
                <Stat title="Approved" value={stats.approved} caption="Hợp đồng đã approve bởi Director" icon={<CheckCircle2 />} tone="green" />
                <Stat title="Actived" value={stats.active} caption="Hợp đồng đang hiện lực" icon={<CheckSquare />} tone="blue" />
                <Stat title="Revision Requested" value={stats.revision} caption="Yêu cầu cần chỉnh sửa" icon={<Pencil />} tone="orange" />
                <Stat title="Rejected" value={stats.rejected} caption="Hợp đồng đã bị từ chối" icon={<XCircle />} tone="red" />
                <Stat title="Expired" value={stats.expired} caption="Hợp đồng đã hết hiệu lực" icon={<Clock3 />} tone="slate" />
                <Stat title="Director Review" value={stats.review} caption="Đang chờ Director xử lý" icon={<Users />} tone="purple" />
            </div>

            <section className="manager-contract-panel">
                <div className="manager-panel-title"><h2>Danh sách hợp đồng</h2></div>
                <div className="manager-filter-bar">
                    <div className="manager-select-wrap"><select value={statusFilter} onChange={(event) => { setPage(1); setStatusFilter(event.target.value); }}><option value="">Trạng thái: Tất cả</option>{statusOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div>
                    <div className="manager-date-wrap"><CalendarDays size={15} /><input type="date" value={dateQuery} onChange={(event) => { setPage(1); setDateQuery(event.target.value); }} aria-label="Thời gian hiệu lực" /></div>
                    <div className="manager-search-wrap"><Search size={16} /><input value={searchQuery} onChange={(event) => { setPage(1); setSearchQuery(event.target.value); }} placeholder="Tìm kiếm mã HĐ, khách hàng..." /></div>
                    <button className="manager-filter-button" title="Bộ lọc" onClick={() => { setPage(1); setStatusFilter(''); setSearchQuery(''); setDateQuery(''); }}><SlidersHorizontal size={16} /></button>
                </div>
                {error && <div className="manager-error">{error}</div>}
                {isLoading ? <div className="manager-loading">Đang tải dữ liệu hợp đồng...</div> : <ContractTable contracts={contracts.filter((item) => managerStatuses.has(item.status))} customers={customers} totalCount={totalContracts} page={page} totalPages={Math.max(1, Math.ceil(totalContracts / PAGE_SIZE))} onPageChange={setPage} managerMode onView={viewContract} />}
            </section>
            {detailData && <ContractDetailModal detail={detailData} customers={customers} onClose={() => setDetailData(null)} />}
        </div>
    );
}

function Stat({ title, value, caption, icon, tone }) {
    return <div className={`manager-stat-card manager-stat-${tone}`}><div><p>{title}</p><strong>{value}</strong><small>{caption}</small></div><span>{icon}</span></div>;
}
