import React, { useState, useEffect } from 'react';

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

const getTodayValue = () => {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
};

const fieldClassName = (hasError) => `w-full border rounded-md px-3 py-2 text-sm focus:ring-1 focus:ring-primary outline-none ${hasError ? 'border-red-400 focus:border-red-500' : 'border-slate-300 focus:border-primary'}`;

function FieldError({ message }) {
    return message ? <p className="mt-1 text-xs text-red-600" role="alert">{message}</p> : null;
}

export default function ContractForm({ 
    initialData = null, 
    customers = [], 
    onClose, 
    onSubmit,
    contractStatus = '',
    existingAttachments = []
}) {
    const [formData, setFormData] = useState({
        customer_id: '',
        effective_from: '',
        effective_to: '',
        contract_value: '',
        payment_terms: '',
        service_terms: '',
        ...initialData
    });
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [currentAttachments, setCurrentAttachments] = useState(existingAttachments || []);
    const [removedAttachmentIds, setRemovedAttachmentIds] = useState([]);
    const [fieldErrors, setFieldErrors] = useState({});

    const isEditMode = !!initialData;
    const isAttachmentEditable = !isEditMode || ['DRAFT', 'REVISION_REQUESTED'].includes(contractStatus);
    const todayValue = getTodayValue();

    useEffect(() => {
        setFormData(prev => ({
            ...prev,
            ...initialData,
        }));
    }, [initialData]);

    useEffect(() => {
        setCurrentAttachments(existingAttachments || []);
        setRemovedAttachmentIds([]);
    }, [existingAttachments]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        setFieldErrors(prev => {
            const next = { ...prev };
            delete next[name];
            if (name === 'effective_from' || name === 'effective_to') {
                delete next.effective_from;
                delete next.effective_to;
            }
            return next;
        });
    };

    const handleFileChange = (e) => {
        const files = Array.from(e.target.files || []);
        if (!files.length) return;

        setSelectedFiles(prev => {
            const next = [...prev];
            files.forEach((file) => {
                const exists = next.some(item => 
                    item.name === file.name && item.size === file.size && item.lastModified === file.lastModified
                );

                if (!exists) {
                    next.push(file);
                }
            });
            return next;
        });

        e.target.value = '';
    };

    const handleRemoveSelectedFile = (fileIndex) => {
        setSelectedFiles(prev => prev.filter((_, index) => index !== fileIndex));
    };

    const handleRemoveCurrentAttachment = (attachment) => {
        if (!attachment?.attachment_id) return;
        setCurrentAttachments(prev => prev.filter(item => item.attachment_id !== attachment.attachment_id));
        setRemovedAttachmentIds(prev => prev.includes(attachment.attachment_id)
            ? prev
            : [...prev, attachment.attachment_id]);
    };

    const handleSubmit = (e) => {
        e.preventDefault();

        const errors = {};
        if (!isEditMode && !formData.customer_id) errors.customer_id = 'Vui lòng chọn khách hàng.';
        if (!formData.effective_from) {
            errors.effective_from = 'Vui lòng chọn ngày bắt đầu hiệu lực.';
        } else if (formData.effective_from < todayValue) {
            errors.effective_from = 'Ngày bắt đầu hiệu lực phải từ hôm nay trở đi.';
        }
        if (!formData.effective_to) {
            errors.effective_to = 'Vui lòng chọn ngày kết thúc hiệu lực.';
        } else if (formData.effective_from && formData.effective_from >= formData.effective_to) {
            errors.effective_to = 'Ngày bắt đầu hiệu lực phải trước ngày kết thúc hiệu lực.';
        }
        if (formData.contract_value === '' || formData.contract_value === null || Number(formData.contract_value) < 0) {
            errors.contract_value = 'Vui lòng nhập giá trị hợp đồng hợp lệ.';
        }
        if (!String(formData.payment_terms || '').trim()) errors.payment_terms = 'Vui lòng nhập điều khoản thanh toán.';
        if (!String(formData.service_terms || '').trim()) errors.service_terms = 'Vui lòng nhập điều khoản dịch vụ.';

        setFieldErrors(errors);
        if (Object.keys(errors).length > 0) return;

        const payload = {
            ...formData,
            payment_terms: formData.payment_terms.trim(),
            service_terms: formData.service_terms.trim(),
            contract_value: parseFloat(formData.contract_value) || 0,
            attachments: selectedFiles,
            ...(isEditMode ? { removed_attachment_ids: removedAttachmentIds } : {}),
        };
        onSubmit(payload);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
                <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                    <h3 className="text-lg font-bold text-slate-800">
                        {isEditMode ? 'Chỉnh sửa hợp đồng' : 'Tạo hợp đồng mới'}
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
                        <i className="fa-solid fa-xmark text-lg"></i>
                    </button>
                </div>
                
                <div className="p-6 overflow-y-auto flex-1">
                    <form id="contract-form" onSubmit={handleSubmit} className="space-y-6" noValidate>
                        {!isEditMode && (
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Khách hàng <span className="text-red-500">*</span></label>
                                <select 
                                    name="customer_id" 
                                    value={formData.customer_id} 
                                    onChange={handleChange}
                                    required
                                    className={fieldClassName(fieldErrors.customer_id)}
                                >
                                    <option value="">-- Chọn khách hàng --</option>
                                    {customers.map(c => (
                                        <option key={c.customer_id} value={c.customer_id}>
                                            {c.company_name} ({c.customer_code})
                                        </option>
                                    ))}
                                </select>
                                <FieldError message={fieldErrors.customer_id} />
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Ngày bắt đầu hiệu lực <span className="text-red-500">*</span></label>
                                <input 
                                    type="date" 
                                    name="effective_from"
                                    value={formData.effective_from}
                                    onChange={handleChange}
                                    required
                                    min={todayValue}
                                    className={fieldClassName(fieldErrors.effective_from)}
                                />
                                <FieldError message={fieldErrors.effective_from} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Ngày kết thúc hiệu lực <span className="text-red-500">*</span></label>
                                <input 
                                    type="date" 
                                    name="effective_to"
                                    value={formData.effective_to}
                                    onChange={handleChange}
                                    required
                                    className={fieldClassName(fieldErrors.effective_to)}
                                />
                                <FieldError message={fieldErrors.effective_to} />
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Giá trị hợp đồng (VND) <span className="text-red-500">*</span></label>
                            <input 
                                type="number" 
                                name="contract_value"
                                value={formData.contract_value}
                                onChange={handleChange}
                                required
                                min="0"
                                step="1000"
                                className={fieldClassName(fieldErrors.contract_value)}
                                placeholder="Ví dụ: 100000000"
                            />
                            <FieldError message={fieldErrors.contract_value} />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Điều khoản thanh toán <span className="text-red-500">*</span></label>
                            <textarea 
                                name="payment_terms"
                                value={formData.payment_terms || ''}
                                onChange={handleChange}
                                rows={3}
                                required
                                className={fieldClassName(fieldErrors.payment_terms)}
                                placeholder="Ghi chú điều khoản thanh toán..."
                            ></textarea>
                            <FieldError message={fieldErrors.payment_terms} />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Điều khoản dịch vụ <span className="text-red-500">*</span></label>
                            <textarea 
                                name="service_terms"
                                value={formData.service_terms || ''}
                                onChange={handleChange}
                                rows={3}
                                required
                                className={fieldClassName(fieldErrors.service_terms)}
                                placeholder="Ghi chú điều khoản dịch vụ..."
                            ></textarea>
                            <FieldError message={fieldErrors.service_terms} />
                        </div>

                        <div className="border border-dashed border-slate-300 rounded-lg p-4 bg-slate-50">
                            <div className="flex items-center justify-between mb-3">
                                <label className="block text-sm font-medium text-slate-700">File đính kèm</label>
                                {isAttachmentEditable ? (
                                    <label className="inline-flex items-center px-3 py-1.5 rounded-md bg-white border border-slate-300 text-sm text-slate-700 hover:bg-slate-100 cursor-pointer">
                                        <i className="fa-solid fa-upload mr-2"></i>
                                        Chọn file
                                        <input
                                            type="file"
                                            multiple
                                            className="hidden"
                                            onChange={handleFileChange}
                                        />
                                    </label>
                                ) : null}
                            </div>

                            {!isAttachmentEditable && (
                                <p className="text-xs text-slate-500 mb-3">
                                    Hợp đồng đang ở trạng thái {contractStatus}. Không cho phép thêm file đính kèm.
                                </p>
                            )}

                            {currentAttachments.length > 0 && (
                                <div className="mb-3 space-y-2">
                                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">File hiện tại</p>
                                    {currentAttachments.map((attachment) => (
                                        <div key={attachment.attachment_id || attachment.file_name} className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
                                            <div className="flex items-center min-w-0">
                                                <i className="fa-solid fa-paperclip text-slate-400 mr-2"></i>
                                                <span className="truncate">{attachment.file_name}</span>
                                            </div>
                                            <div className="flex items-center gap-2 ml-3">
                                                <span className="text-xs text-slate-500">{formatFileSize(attachment.file_size)}</span>
                                                {isAttachmentEditable && (
                                                    <button
                                                        type="button"
                                                        onClick={() => handleRemoveCurrentAttachment(attachment)}
                                                        className="text-slate-400 hover:text-red-500"
                                                        title="Xóa file khỏi phiên bản mới"
                                                        aria-label={`Xóa ${attachment.file_name}`}
                                                    >
                                                        <i className="fa-solid fa-xmark"></i>
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {selectedFiles.length > 0 && (
                                <div className="space-y-2">
                                    <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">File mới</p>
                                    {selectedFiles.map((file, index) => (
                                        <div key={`${file.name}-${file.size}-${file.lastModified}-${index}`} className="flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
                                            <div className="flex items-center min-w-0">
                                                <i className="fa-solid fa-file-lines text-slate-400 mr-2"></i>
                                                <span className="truncate">{file.name}</span>
                                            </div>
                                            <div className="flex items-center gap-2 ml-3">
                                                <span className="text-xs text-slate-500">{formatFileSize(file.size)}</span>
                                                <button
                                                    type="button"
                                                    onClick={() => handleRemoveSelectedFile(index)}
                                                    className="text-slate-400 hover:text-red-500"
                                                    title="Xóa file"
                                                >
                                                    <i className="fa-solid fa-xmark"></i>
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {selectedFiles.length === 0 && currentAttachments.length === 0 && (
                                <p className="text-sm text-slate-500">Chưa có file nào được đính kèm.</p>
                            )}

                            <p className="mt-2 text-[11px] text-slate-500">
                                Định dạng hỗ trợ: PDF, DOC, DOCX, XLS, XLSX, PNG, JPG, JPEG (tối đa 10MB/file)
                            </p>
                        </div>
                    </form>
                </div>
                
                <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex justify-end space-x-3">
                    <button 
                        onClick={onClose}
                        className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-100 transition-colors"
                    >
                        Hủy bỏ
                    </button>
                    <button 
                        form="contract-form"
                        type="submit"
                        className="px-4 py-2 bg-primary text-white rounded-md text-sm font-medium hover:bg-teal-700 transition-colors shadow-sm"
                    >
                        {isEditMode ? 'Cập nhật' : 'Tạo mới'}
                    </button>
                </div>
            </div>
        </div>
    );
}
