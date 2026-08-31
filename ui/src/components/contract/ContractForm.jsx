import React, { useState, useEffect } from 'react';

export default function ContractForm({ 
    initialData = null, 
    customers = [], 
    onClose, 
    onSubmit 
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

    const isEditMode = !!initialData;

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        // convert contract_value to number
        const payload = {
            ...formData,
            contract_value: parseFloat(formData.contract_value) || 0
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
