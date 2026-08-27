import React from 'react';

export default function EditVolumeModal({ isOpen, onClose }) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
            <div className="bg-white w-full max-w-lg rounded-xl shadow-xl overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-white">
                    <h3 className="font-bold text-lg text-slate-800">Điều chỉnh sản lượng</h3>
                    <button className="text-slate-400 hover:text-slate-600" onClick={onClose}><i className="fa-solid fa-xmark text-xl"></i></button>
                </div>
                <div className="p-6">
                    <form>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-slate-700 mb-2">Dịch vụ điều chỉnh</label>
                            <div className="p-3 bg-slate-50 rounded-lg text-sm text-slate-800 font-medium border border-slate-200">
                                Bốc xếp container 20ft (Hàng nhập) (SRV-20ft-IN)
                            </div>
                        </div>
                        <div className="mb-4">
                            <label className="block text-sm font-medium text-slate-700 mb-2">Số lượng mới</label>
                            <input type="number" min="0.01" step="0.01" required className="w-full border border-slate-300 rounded-lg px-4 py-2 outline-none focus:border-primary text-sm" defaultValue={50} />
                        </div>
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-slate-700 mb-2">Lý do điều chỉnh (Bắt buộc)</label>
                            <textarea rows="3" required className="w-full border border-slate-300 rounded-lg px-4 py-2 outline-none focus:border-primary text-sm" placeholder="Nhập lý do..."></textarea>
                        </div>
                        <div className="flex justify-end space-x-3">
                            <button type="button" className="px-4 py-2 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-50 text-sm font-medium" onClick={onClose}>Hủy</button>
                            <button type="button" className="px-4 py-2 rounded-lg bg-primary text-white hover:bg-teal-700 text-sm font-medium shadow-sm" onClick={onClose}>Cập nhật</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
