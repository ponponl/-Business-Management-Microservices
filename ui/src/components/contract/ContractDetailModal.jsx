import React from 'react';
import { useToast } from '../common/ToastContext';

const BASE_URL = 'http://localhost:8080/api/v1';

const formatFileSize = (bytes = 0) => {
    if (!bytes) return '0 KB';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex += 1;
    }

    return `${size.toFixed(size >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
};

export default function ContractDetailModal({ detail, customers, onClose, viewerRole = 'STAFF' }) {
    const toast = useToast();
    if (!detail) return null;

    const customer = customers.find(c => c.customer_id === detail.customer_id) || {};
    const attachments = Array.isArray(detail.attachments) ? detail.attachments : [];
    const viewerKey = viewerRole.toLowerCase();
    const revisionReason = detail[`revision_reason_for_${viewerKey}`] || null;
    const revisionReasonSource = detail[`revision_reason_source_for_${viewerKey}`] || null;
    const revisionLabel = revisionReasonSource === 'DIRECTOR' ? 'Director' : 'Manager';

    const formatDateValue = (value) => {
        if (!value) return 'N/A';

        const normalized = typeof value === 'string' ? value.split('T')[0] : value;
        const match = /^\d{4}-\d{2}-\d{2}$/.exec(String(normalized));
        if (!match) {
            const parsed = new Date(value);
            return Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleDateString('vi-VN');
        }
        const [year, month, day] = normalized.split('-');
        return `${day}/${month}/${year}`;
    };

    const handleDownloadAttachment = async (attachment) => {
        if (!attachment?.attachment_id) {
            return;
        }

        const token = localStorage.getItem('token') || JSON.parse(localStorage.getItem('user_info') || '{}').token || '';

        try {
            const response = await fetch(`${BASE_URL}/contracts/${detail.contract_id}/attachments/${attachment.attachment_id}`, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
            });

            if (!response.ok) {
                throw new Error('Không thể tải file đính kèm');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = attachment.file_name || 'attachment';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            toast.success('Tải file đính kèm thành công.');
        } catch (error) {
            toast.error(error.message || 'Không thể tải file đính kèm.');
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-3xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                    <h3 className="text-lg font-bold text-slate-800">
                        Chi tiết Hợp đồng {detail.contract_number}
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <i className="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>
                
                <div className="p-6 overflow-y-auto flex-1 bg-white">
                    <div className="grid grid-cols-2 gap-6 mb-6">
                        <div>
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Thông tin Hợp đồng</h4>
                            <div className="space-y-3 text-sm">
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Mã hợp đồng:</span>
                                    <span className="w-2/3 font-medium text-slate-800">{detail.contract_number}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Trạng thái:</span>
                                    <span className="w-2/3 font-semibold text-primary">{detail.status}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Giá trị:</span>
                                    <span className="w-2/3 font-medium text-slate-800">
                                        {new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(detail.current_version_detail?.contract_value || 0)}
                                    </span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Ngày tạo:</span>
                                    <span className="w-2/3 text-slate-800">{formatDateValue(detail.created_at)}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Hiệu lực từ:</span>
                                    <span className="w-2/3 text-slate-800">{formatDateValue(detail.current_version_detail?.effective_from)}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Hiệu lực đến:</span>
                                    <span className="w-2/3 text-slate-800">{formatDateValue(detail.current_version_detail?.effective_to)}</span>
                                </div>
                            </div>
                        </div>

                        <div>
                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Thông tin Khách hàng</h4>
                            <div className="space-y-3 text-sm">
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Tên công ty:</span>
                                    <span className="w-2/3 font-medium text-slate-800">{customer.company_name || detail.customer_id}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Mã KH:</span>
                                    <span className="w-2/3 text-slate-800">{customer.customer_code || 'N/A'}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Mã số thuế:</span>
                                    <span className="w-2/3 text-slate-800">{customer.tax_code || 'N/A'}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Email:</span>
                                    <span className="w-2/3 text-slate-800">{customer.email || 'N/A'}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="mb-6">
                        {revisionReason && <div className="mb-4 rounded-lg border border-orange-200 bg-orange-50 p-4 text-sm text-orange-800"><strong>Yêu cầu chỉnh sửa từ {revisionLabel}</strong><p className="mt-1 whitespace-pre-wrap">{revisionReason}</p></div>}
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Điều khoản thanh toán</h4>
                        <div className="p-4 bg-slate-50 rounded-lg text-sm text-slate-700 whitespace-pre-wrap border border-slate-100">
                            {detail.current_version_detail?.payment_terms || 'Không có điều khoản thanh toán.'}
                        </div>
                    </div>

                    <div className="mb-6">
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Điều khoản dịch vụ</h4>
                        <div className="p-4 bg-slate-50 rounded-lg text-sm text-slate-700 whitespace-pre-wrap border border-slate-100">
                            {detail.current_version_detail?.service_terms || 'Không có điều khoản dịch vụ.'}
                        </div>
                    </div>

                    <div>
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">File đính kèm</h4>
                        {attachments.length > 0 ? (
                            <div className="space-y-2">
                                {attachments.map((attachment) => (
                                    <div key={attachment.attachment_id || attachment.file_name} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                                        <div className="flex items-center min-w-0">
                                            <i className="fa-solid fa-paperclip text-slate-400 mr-2"></i>
                                            <span className="text-sm text-slate-700 truncate">{attachment.file_name}</span>
                                        </div>
                                        <div className="flex items-center gap-2 ml-3 shrink-0">
                                            <span className="text-xs text-slate-500">{formatFileSize(attachment.file_size)}</span>
                                            <button
                                                type="button"
                                                onClick={() => handleDownloadAttachment(attachment)}
                                                className="px-2 py-1 text-xs font-medium rounded border border-slate-300 text-slate-700 hover:bg-white transition-colors"
                                            >
                                                Tải xuống
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="p-4 bg-slate-50 rounded-lg text-sm text-slate-500 border border-slate-100">
                                Không có file đính kèm cho phiên bản hiện tại.
                            </div>
                        )}
                    </div>
                </div>
                
                <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end">
                    <button 
                        onClick={onClose}
                        className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-100 transition-colors"
                    >
                        Đóng
                    </button>
                </div>
            </div>
        </div>
    );
}
