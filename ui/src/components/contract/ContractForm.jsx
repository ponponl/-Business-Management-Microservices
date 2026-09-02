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

    const isEditMode = !!initialData;
    const isAttachmentEditable = !isEditMode || ['DRAFT', 'REVISION_REQUESTED'].includes(contractStatus);

    useEffect(() => {
        setFormData(prev => ({
            ...prev,
            ...initialData,
        }));
    }, [initialData]);

    useEffect(() => {
        setCurrentAttachments(existingAttachments || []);
    }, [existingAttachments]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
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

    const handleSubmit = (e) => {
        e.preventDefault();
        const payload = {
            ...formData,
            contract_value: parseFloat(formData.contract_value) || 0,
            attachments: selectedFiles,
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
                    <form id="contract-form" onSubmit={handleSubmit} className="space-y-6">
                        {!isEditMode && (
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Khách hàng <span className="text-red-500">*</span></label>
                                <select 
                                    name="customer_id" 
                                    value={formData.customer_id} 
                                    onChange={handleChange}
                                    required
                                    className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                                >
                                    <option value="">-- Chọn khách hàng --</option>
                                    {customers.map(c => (
                                        <option key={c.customer_id} value={c.customer_id}>
                                            {c.company_name} ({c.customer_code})
                                        </option>
                                    ))}
                                </select>
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
                                    className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Ngày kết thúc hiệu lực <span className="text-red-500">*</span></label>
                                <input 
                                    type="date" 
                                    name="effective_to"
                                    value={formData.effective_to}
                                    onChange={handleChange}
                                    required
                                    className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                                />
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
                                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                                placeholder="Ví dụ: 100000000"
                            />
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Điều khoản thanh toán</label>
                            <textarea 
                                name="payment_terms"
                                value={formData.payment_terms}
                                onChange={handleChange}
                                rows={3}
                                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                                placeholder="Ghi chú điều khoản thanh toán..."
                            ></textarea>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-1">Điều khoản dịch vụ</label>
                            <textarea 
                                name="service_terms"
                                value={formData.service_terms}
                                onChange={handleChange}
                                rows={3}
                                className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:border-primary focus:ring-1 focus:ring-primary outline-none"
                                placeholder="Ghi chú điều khoản dịch vụ..."
                            ></textarea>
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
                                            <span className="text-xs text-slate-500 ml-3">{formatFileSize(attachment.file_size)}</span>
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
