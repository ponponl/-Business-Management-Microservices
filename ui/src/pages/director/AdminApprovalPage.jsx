import React, { useState } from 'react';
import { Layers, Hourglass, CheckCircle2, XCircle, Eye, Search, Download, Check, X, FileSpreadsheet, PackageCheck } from 'lucide-react';

const INITIAL_DATA = [
  {
    id: 'PL-2026-001',
    uuid: '867d703e-28ad-4cc2-b041-cf533a6d8ae4',
    name: 'Cảng Cát Lái',
    type: 'CUSTOMER',
    version: 'v3.0',
    effectiveDate: '01/01/2026 - 31/12/2026',
    status: 'SUBMITTED',
    creator: 'Nguyễn Văn A',
    updatedBy: 'Hệ thống',
    updatedAt: '01/01/2026',
    services: [
      { code: 'DV-LIF-20', name: 'Nâng hạ Container 20ft', unit: 'Cont', price: '450,000', currency: 'VNĐ' },
      { code: 'DV-LIF-40', name: 'Nâng hạ Container 40ft', unit: 'Cont', price: '680,000', currency: 'VNĐ' },
      { code: 'DV-STO-01', name: 'Lưu kho bãi bãi thường', unit: 'Tấn/Ngày', price: '120,000', currency: 'VNĐ' }
    ]
  },
  {
    id: 'PL-2026-006',
    uuid: 'da09008a-4931-4a3b-82e3-44256e391966',
    name: 'Tập đoàn Hòa Phát',
    type: 'SERVICE_GROUP',
    version: 'v1.0',
    effectiveDate: '15/06/2026 - 15/06/2027',
    status: 'SUBMITTED',
    creator: 'Trần Văn C',
    updatedBy: 'Hệ thống',
    updatedAt: '15/06/2026',
    services: [
      { code: 'DV-STE-01', name: 'Bốc xếp thép cuộn nhập khẩu', unit: 'Tấn', price: '85,000', currency: 'VNĐ' },
      { code: 'DV-STE-02', name: 'Vận chuyển thép nội địa', unit: 'Chuyến', price: '2,500,000', currency: 'VNĐ' }
    ]
  },
  {
    id: 'PL-2026-003',
    uuid: '294520bd-9824-47d7-8e32-d00e9ecc43c8',
    name: 'Cảng Cái Mép Thượng',
    type: 'GENERAL',
    version: 'v2.0',
    effectiveDate: '01/06/2026 - 30/06/2026',
    status: 'EFFECTIVE',
    creator: 'Lê Thị B',
    updatedBy: 'Admin',
    updatedAt: '01/06/2026',
    services: [
      { code: 'DV-GEN-01', name: 'Phí hoa tiêu cảng biển', unit: 'Lượt', price: '5,000,000', currency: 'VNĐ' },
      { code: 'DV-GEN-02', name: 'Phí buộc cởi dây tàu', unit: 'Lượt', price: '1,200,000', currency: 'VNĐ' }
    ]
  },
  {
    id: 'PL-2026-004',
    uuid: 'b1050e18-ccb8-415c-af8f-66f79f76e1e3',
    name: 'Cty TNHH Vận tải Phương Nam',
    type: 'CUSTOMER',
    version: 'v1.0',
    effectiveDate: '01/06/2026 - 30/06/2026',
    status: 'REJECTED',
    creator: 'Nguyễn Văn A',
    updatedBy: 'Admin',
    updatedAt: '01/06/2026',
    services: [
      { code: 'DV-TRK-01', name: 'Vận tải xe đầu kéo Cát Lái - Bình Dương', unit: 'Chuyến', price: '3,100,000', currency: 'VNĐ' }
    ]
  }
];

export default function AdminApprovalPage() {
  const [data, setData] = useState(INITIAL_DATA);
  const [statusFilter, setStatusFilter] = useState('SUBMITTED');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);

  const [modalConfig, setModalConfig] = useState({
    isOpen: false,
    type: '',
    title: '',
    message: '',
    btnText: 'Đóng'
  });

  const totalCount = data.length;
  const submittedCount = data.filter((i) => i.status === 'SUBMITTED').length;
  const effectiveCount = data.filter((i) => i.status === 'EFFECTIVE').length;
  const rejectedCount = data.filter((i) => i.status === 'REJECTED').length;

  const filteredData = data.filter((item) => {
    const matchStatus = statusFilter === 'ALL' || item.status === statusFilter;
    const matchType = typeFilter === 'ALL' || item.type === typeFilter;
    const matchSearch = item.id.toLowerCase().includes(searchTerm.toLowerCase()) || item.name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchStatus && matchType && matchSearch;
  });

  const handleAction = (item, newStatus) => {
    setData(
      data.map((i) =>
        i.id === item.id ? { ...i, status: newStatus, updatedBy: 'Admin (Bạn)', updatedAt: new Date().toLocaleDateString('vi-VN') } : i
      )
    );

    if (selectedItem?.id === item.id) setSelectedItem(null);

    if (newStatus === 'EFFECTIVE') {
      setModalConfig({
        isOpen: true,
        type: 'approve',
        title: 'Đã phê duyệt bảng giá!',
        message: `Bảng giá ${item.id} (${item.name}) đã chuyển sang trạng thái Hiệu lực (EFFECTIVE).`,
        btnText: 'Xác nhận'
      });
    } else {
      setModalConfig({
        isOpen: true,
        type: 'reject',
        title: 'Đã từ chối bảng giá!',
        message: `Bảng giá ${item.id} (${item.name}) đã bị từ chối (REJECTED).`,
        btnText: 'Đóng'
      });
    }
  };

  return (
    <div className="space-y-5 font-sans text-slate-700 max-w-[1400px] mx-auto relative pb-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Quản lý phê duyệt đơn giá</h1>
          <p className="text-xs text-slate-500 mt-0.5">Hệ thống thẩm định, phê duyệt và quản lý lịch sử hiệu lực bảng giá dịch vụ logistics.</p>
        </div>
        <button className="px-3.5 py-2 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-semibold flex items-center space-x-2 shadow-xs cursor-pointer">
          <Download className="w-4 h-4 text-slate-500" />
          <span>Xuất Excel</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="flex flex-row items-center gap-4 w-full">
        <div className="flex-1 bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between min-w-0">
          <div>
            <p className="text-[11px] font-medium text-slate-500 whitespace-nowrap">Tổng số bảng giá</p>
            <p className="text-2xl font-bold text-slate-800 mt-1">{totalCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-slate-50 flex-shrink-0 flex items-center justify-center text-slate-400 border border-slate-100">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="flex-1 bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between min-w-0">
          <div>
            <p className="text-[11px] font-medium text-amber-600 whitespace-nowrap">Chờ duyệt (SUBMITTED)</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{submittedCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex-shrink-0 flex items-center justify-center text-amber-500 border border-amber-100">
            <Hourglass className="w-5 h-5" />
          </div>
        </div>

        <div className="flex-1 bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between min-w-0">
          <div>
            <p className="text-[11px] font-medium text-emerald-600 whitespace-nowrap">Hiệu lực (EFFECTIVE)</p>
            <p className="text-2xl font-bold text-emerald-600 mt-1">{effectiveCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex-shrink-0 flex items-center justify-center text-emerald-500 border border-emerald-100">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="flex-1 bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between min-w-0">
          <div>
            <p className="text-[11px] font-medium text-rose-600 whitespace-nowrap">Bị từ chối (REJECTED)</p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{rejectedCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-rose-50 flex-shrink-0 flex items-center justify-center text-rose-500 border border-rose-100">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Bộ Lọc & Tìm Kiếm */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between gap-4">
        <div className="flex items-center space-x-2 text-xs">
          <span className="text-slate-500">Loại áp dụng:</span>
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none bg-slate-50/50 font-medium text-slate-700">
            <option value="ALL">Tất cả</option>
            <option value="CUSTOMER">CUSTOMER</option>
            <option value="SERVICE_GROUP">SERVICE_GROUP</option>
            <option value="GENERAL">GENERAL</option>
          </select>
        </div>

        <div className="flex items-center space-x-3">
          <div className="bg-slate-100/80 p-1 rounded-lg flex items-center space-x-1 text-xs">
            {[
              { key: 'ALL', label: 'Tất cả' },
              { key: 'SUBMITTED', label: 'SUBMITTED' },
              { key: 'EFFECTIVE', label: 'EFFECTIVE' },
              { key: 'REJECTED', label: 'REJECTED' }
            ].map((tab) => (
              <button key={tab.key} onClick={() => setStatusFilter(tab.key)} className={`px-3 py-1 rounded-md font-semibold transition cursor-pointer ${statusFilter === tab.key ? 'bg-white text-amber-600 shadow-xs' : 'text-slate-500 hover:text-slate-800'}`}>
                {tab.label}
              </button>
            ))}
          </div>

          <div className="relative w-56">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="Tìm kiếm..." className="w-full pl-8 pr-3 py-1.5 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-amber-500 bg-white" />
          </div>
        </div>
      </div>

      {/* Bảng dữ liệu chính */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-50/70 border-b border-slate-200 text-slate-500 font-bold">
              <th className="py-3 px-4">Mã bảng giá</th>
              <th className="py-3 px-4">Tên bảng giá / Đối tượng</th>
              <th className="py-3 px-4">Loại áp dụng</th>
              <th className="py-3 px-4">Phiên bản</th>
              <th className="py-3 px-4">Thời gian hiệu lực</th>
              <th className="py-3 px-4">Trạng thái</th>
              <th className="py-3 px-4">Cập nhật</th>
              <th className="py-3 px-4 text-center">Hành động</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-slate-100">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan="8" className="text-center py-10 text-slate-400">
                  <FileSpreadsheet className="w-7 h-7 mx-auto mb-2 opacity-30" />
                  Không có dữ liệu bảng giá phù hợp.
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3 px-4 font-bold text-slate-800">{item.id}</td>
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-800">{item.name}</div>
                    <div className="text-[10px] text-slate-400 font-mono tracking-tight">{item.uuid}</div>
                  </td>
                  <td className="py-3 px-4">
                    <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium text-[10px] uppercase border border-slate-200">{item.type}</span>
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-600">{item.version}</td>
                  <td className="py-3 px-4 text-slate-600">{item.effectiveDate}</td>
                  <td className="py-3 px-4">
                    {item.status === 'SUBMITTED' && <span className="bg-sky-50 text-sky-600 px-2.5 py-0.5 rounded-full font-bold text-[10px] border border-sky-200">SUBMITTED</span>}
                    {item.status === 'EFFECTIVE' && <span className="bg-emerald-50 text-emerald-600 px-2.5 py-0.5 rounded-full font-bold text-[10px] border border-emerald-200">EFFECTIVE</span>}
                    {item.status === 'REJECTED' && <span className="bg-rose-50 text-rose-600 px-2.5 py-0.5 rounded-full font-bold text-[10px] border border-rose-200">REJECTED</span>}
                  </td>
                  <td className="py-3 px-4 text-[11px]">
                    <div className="text-slate-700 font-medium">{item.updatedBy}</div>
                    <div className="text-slate-400 text-[10px]">{item.updatedAt}</div>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <div className="flex items-center justify-center space-x-1.5">
                      <button onClick={() => setSelectedItem(item)} className="p-1 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-md transition cursor-pointer" title="Xem chi tiết dịch vụ">
                        <Eye className="w-4 h-4" />
                      </button>

                      {item.status === 'SUBMITTED' && (
                        <>
                          <button onClick={() => handleAction(item, 'EFFECTIVE')} className="p-1 bg-emerald-50 hover:bg-emerald-600 text-emerald-600 hover:text-white border border-emerald-200 rounded-md transition cursor-pointer" title="Phê duyệt">
                            <Check className="w-4 h-4" />
                          </button>
                          <button onClick={() => handleAction(item, 'REJECTED')} className="p-1 bg-rose-50 hover:bg-rose-600 text-rose-600 hover:text-white border border-rose-200 rounded-md transition cursor-pointer" title="Từ chối">
                            <X className="w-4 h-4" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Modal Xem Chi Tiết */}
      {selectedItem && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-[92vw] max-w-[720px] p-4 shadow-2xl space-y-3 max-h-[80vh] flex flex-col animate-in fade-in zoom-in-95 duration-150 border border-slate-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="text-[11px] font-mono text-amber-600 font-bold bg-amber-50 px-2 py-0.5 rounded border border-amber-200">{selectedItem.id}</span>
                  <span className="text-[11px] text-slate-400 font-medium">Phiên bản {selectedItem.version}</span>
                </div>
                <h3 className="text-base font-bold text-slate-900 mt-1">{selectedItem.name}</h3>
              </div>
              <button onClick={() => setSelectedItem(null)} className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-3 text-xs bg-slate-50 p-3 rounded-xl border border-slate-100">
              <div>
                <span className="text-slate-400 block text-[11px]">Người đề xuất:</span>
                <span className="font-semibold text-slate-700">{selectedItem.creator}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Thời gian hiệu lực:</span>
                <span className="font-semibold text-slate-700">{selectedItem.effectiveDate}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Loại áp dụng:</span>
                <span className="font-semibold text-slate-700">{selectedItem.type}</span>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-700">
                <PackageCheck className="w-4 h-4 text-amber-500" />
                <span>Danh sách đơn giá dịch vụ ({selectedItem.services?.length || 0})</span>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-100/80 text-slate-600 font-semibold border-b border-slate-200">
                      <th className="py-2.5 px-3">Mã dịch vụ</th>
                      <th className="py-2.5 px-3">Tên dịch vụ</th>
                      <th className="py-2.5 px-3">Đơn vị tính</th>
                      <th className="py-2.5 px-3 text-right">Đơn giá</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {selectedItem.services && selectedItem.services.length > 0 ? (
                      selectedItem.services.map((srv, idx) => (
                        <tr key={idx} className="hover:bg-slate-50/80">
                          <td className="py-2.5 px-3 font-mono text-slate-600 font-semibold">{srv.code}</td>
                          <td className="py-2.5 px-3 font-medium text-slate-800">{srv.name}</td>
                          <td className="py-2.5 px-3 text-slate-500">{srv.unit}</td>
                          <td className="py-2.5 px-3 text-right font-bold text-slate-900">
                            {srv.price} <span className="text-[10px] text-slate-400 font-normal">{srv.currency}</span>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="4" className="text-center py-4 text-slate-400">Không có thông tin dịch vụ.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
              <button onClick={() => setSelectedItem(null)} className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg text-xs font-semibold transition cursor-pointer">
                Đóng
              </button>
              {selectedItem.status === 'SUBMITTED' && (
                <>
                  <button 
                    onClick={() => handleAction(selectedItem, 'REJECTED')} 
                    style={{ backgroundColor: '#e11d48', color: '#ffffff', border: 'none' }}
                    className="px-4 py-2 rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                  >
                    Từ chối
                  </button>
                  <button 
                    onClick={() => handleAction(selectedItem, 'EFFECTIVE')} 
                    style={{ backgroundColor: '#059669', color: '#ffffff', border: 'none' }}
                    className="px-4 py-2 rounded-lg text-xs font-semibold shadow-xs transition cursor-pointer"
                  >
                    Phê duyệt ngay
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal Thông Báo - Ép màu nền Inline Style trực tiếp đè CSS bị trùng */}
      {modalConfig.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-xl border border-slate-100 max-w-sm w-full p-6 text-center space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex justify-center">
              <div
                className={`w-14 h-14 rounded-full flex items-center justify-center ${
                  modalConfig.type === 'approve'
                    ? 'bg-emerald-100 text-emerald-600'
                    : 'bg-rose-100 text-rose-600'
                }`}
              >
                {modalConfig.type === 'approve' ? (
                  <Check className="w-8 h-8 stroke-[3]" />
                ) : (
                  <X className="w-8 h-8 stroke-[3]" />
                )}
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-base font-bold text-slate-900">{modalConfig.title}</h3>
              <p className="text-xs text-slate-500 leading-relaxed">{modalConfig.message}</p>
            </div>

            <button
              type="button"
              onClick={() => setModalConfig({ ...modalConfig, isOpen: false })}
              style={{
                backgroundColor: modalConfig.type === 'approve' ? '#059669' : '#e11d48',
                color: '#ffffff',
                border: 'none'
              }}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-bold shadow-md transition cursor-pointer active:scale-95"
            >
              {modalConfig.btnText}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}