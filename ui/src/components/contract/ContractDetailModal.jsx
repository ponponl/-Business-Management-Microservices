import React from 'react';

export default function ContractDetailModal({ detail, customers, onClose }) {
    if (!detail) return null;

    const customer = customers.find(c => c.customer_id === detail.customer_id) || {};

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
                                    <span className="w-1/3 text-slate-500">Hiệu lực từ:</span>
                                    <span className="w-2/3 text-slate-800">{detail.current_version_detail?.effective_from}</span>
                                </div>
                                <div className="flex">
                                    <span className="w-1/3 text-slate-500">Hiệu lực đến:</span>
                                    <span className="w-2/3 text-slate-800">{detail.current_version_detail?.effective_to}</span>
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
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Điều khoản thanh toán</h4>
                        <div className="p-4 bg-slate-50 rounded-lg text-sm text-slate-700 whitespace-pre-wrap border border-slate-100">
                            {detail.current_version_detail?.payment_terms || 'Không có điều khoản thanh toán.'}
                        </div>
                    </div>

                    <div>
                        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Điều khoản dịch vụ</h4>
                        <div className="p-4 bg-slate-50 rounded-lg text-sm text-slate-700 whitespace-pre-wrap border border-slate-100">
                            {detail.current_version_detail?.service_terms || 'Không có điều khoản dịch vụ.'}
                        </div>
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
