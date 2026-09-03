import React from 'react';

export default function ContractTable({ 
    contracts = [], 
    customers = [], 
    totalCount = contracts.length,
    onView, 
    onEdit, 
    onSubmit, 
    onCancel,
    managerMode = false,
    page = 1,
    pageSize = 20,
    totalPages = 1,
    onPageChange,
}) {
    const formatDateForDisplay = (value) => {
        if (value === null || value === undefined || value === '') return 'N/A';

        const asString = String(value).trim();
        if (!asString) return 'N/A';

        const dateOnly = asString.includes('T') ? asString.split('T')[0] : asString;
        const match = /^\d{4}-\d{2}-\d{2}$/.exec(dateOnly);

        if (match) {
            const [year, month, day] = dateOnly.split('-');
            return `${day}/${month}/${year}`;
        }

        const parsed = new Date(asString);
        if (Number.isNaN(parsed.getTime())) {
            return asString;
        }

        return parsed.toLocaleDateString('vi-VN');
    };

    const formatDateRange = (from, to) => {
        const rawFrom = from ?? '';
        const rawTo = to ?? '';

        if (!rawFrom && !rawTo) return 'N/A';
        if (!rawFrom || !rawTo) return formatDateForDisplay(rawFrom || rawTo);

        return `${formatDateForDisplay(rawFrom)} - ${formatDateForDisplay(rawTo)}`;
    };

    const getCustomerName = (customerId) => {
        const customer = customers.find(c => c.customer_id === customerId);
        return customer ? customer.company_name : customerId;
    };

    const getStatusBadge = (status) => {
        switch(status) {
            case 'DRAFT': 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-yellow-100 text-yellow-700">DRAFT</span>;
            case 'SUBMITTED': 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-orange-100 text-orange-700">SUBMITTED</span>;
            case 'DIRECTOR_REVIEW':
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-purple-100 text-purple-700">DIRECTOR_REVIEW</span>;
            case 'APPROVED': 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-green-100 text-green-700">APPROVED</span>;
            case 'ACTIVE': 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-emerald-100 text-emerald-700">ACTIVE</span>;
            case 'REJECTED': 
            case 'CANCELLED': 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-red-100 text-red-700">{status}</span>;
            case 'EXPIRED': 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-gray-100 text-gray-700">EXPIRED</span>;
            default: 
                return <span className="px-2 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-600">{status}</span>;
        }
    };

    return (
        <div className={managerMode ? 'contract-table-manager' : 'bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden'}>
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse whitespace-nowrap">
                    <thead>
                        <tr className="bg-white text-slate-500 text-[11px] uppercase tracking-wider border-b border-slate-200">
                            <th className="px-6 py-4 font-semibold">Số hợp đồng</th>
                            <th className="px-6 py-4 font-semibold">Khách hàng</th>
                            <th className="px-6 py-4 font-semibold">Thời gian hiệu lực</th>
                            <th className="px-6 py-4 font-semibold text-right">Giá trị hợp đồng</th>
                            <th className="px-6 py-4 font-semibold text-center">Trạng thái</th>
                            <th className="px-6 py-4 font-semibold text-right">{managerMode ? 'Xem chi tiết' : 'Hành động'}</th>
                        </tr>
                    </thead>
                    <tbody className="text-sm">
                        {contracts.length > 0 ? contracts.map((c) => (
                            <tr key={c.contract_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                                <td className="px-6 py-4 font-semibold text-primary">{c.contract_number}</td>
                                <td className="px-6 py-4 font-medium text-slate-700">
                                    <div className="flex flex-col">
                                        <span>{getCustomerName(c.customer_id)}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-slate-500">
                                    {formatDateRange(
                                        c.effective_from ?? c.effectiveFrom ?? c.date_from ?? c.dateFrom ?? c.valid_from ?? c.validFrom ?? c.current_version_detail?.effective_from,
                                        c.effective_to ?? c.effectiveTo ?? c.date_to ?? c.dateTo ?? c.valid_to ?? c.validTo ?? c.current_version_detail?.effective_to
                                    )}
                                </td>
                                <td className="px-6 py-4 text-right font-semibold text-slate-700">
                                    {c.contract_value ? new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(c.contract_value) : 'N/A'}
                                </td>
                                <td className="px-6 py-4 text-center">{getStatusBadge(c.status)}</td>
                                <td className="px-6 py-4 text-right space-x-2">
                                    <button onClick={() => onView(c.contract_id)} className="text-slate-400 hover:text-primary transition-colors" title="Xem chi tiết"><i className="fa-solid fa-eye"></i></button>
                                    {!managerMode && c.status === 'DRAFT' && (
                                        <>
                                            <button onClick={() => onEdit(c.contract_id)} className="text-slate-400 hover:text-amber-500 transition-colors" title="Chỉnh sửa"><i className="fa-solid fa-pen-to-square"></i></button>
                                            <button onClick={() => onSubmit(c.contract_id)} className="text-slate-400 hover:text-green-500 transition-colors" title="Submit"><i className="fa-solid fa-paper-plane"></i></button>
                                            <button onClick={() => onCancel(c.contract_id)} className="text-slate-400 hover:text-red-500 transition-colors" title="Cancel"><i className="fa-solid fa-xmark"></i></button>
                                        </>
                                    )}
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="6" className="px-6 py-10 text-center text-slate-500">
                                    Không có dữ liệu hợp đồng nào
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
            
            {/* Pagination Placeholder */}
            <div className="p-4 border-t border-slate-200 flex items-center justify-between text-sm text-slate-500 bg-white">
                <div>Hiển thị {totalCount ? (page - 1) * pageSize + 1 : 0} - {(page - 1) * pageSize + contracts.length} của {totalCount} hợp đồng</div>
                <div className="flex space-x-1">
                    <button onClick={() => onPageChange?.(page - 1)} disabled={page <= 1} className="w-8 h-8 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50 disabled:opacity-40"><i className="fa-solid fa-chevron-left text-xs"></i></button>
                    <button className="w-8 h-8 rounded bg-sidebar text-white flex items-center justify-center font-medium">{page}</button>
                    <button onClick={() => onPageChange?.(page + 1)} disabled={page >= totalPages} className="w-8 h-8 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50 disabled:opacity-40"><i className="fa-solid fa-chevron-right text-xs"></i></button>
                </div>
            </div>
        </div>
    );
}
