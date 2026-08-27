import React, { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  Plus,
  RefreshCw,
  Calendar,
  ExternalLink,
} from "lucide-react";

const API_BASE_URL = "http://localhost:8082/api/v1/price-history";

/**
 */
const formatDate = (dateString, includeTime = false) => {
  if (!dateString || dateString === "---" || dateString === null) return "---";

  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) {
      return dateString;
    }

    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();

    if (includeTime) {
      const hours = String(date.getHours()).padStart(2, "0");
      const minutes = String(date.getMinutes()).padStart(2, "0");
      return `${day}/${month}/${year} ${hours}:${minutes}`;
    }

    return `${day}/${month}/${year}`;
  } catch (error) {
    return dateString;
  }
};

export const PriceListHistoryDetail = ({
  priceListId: propPriceListId,
  user,
  onBack,
  onNavigateToChangeLogs,
  onNavigateToUsageLogs,
}) => {
  const navigate = useNavigate();
  const params = useParams();

  const priceListId = propPriceListId || params.priceListId || params.id;

  const [versions, setVersions] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [selectedVersionsForCompare, setSelectedVersionsForCompare] = useState([]);

  const [activeTab, setActiveTab] = useState("details"); // 'details' | 'changes' | 'usage'

  const [versionDetail, setVersionDetail] = useState(null);
  const [changeLogs, setChangeLogs] = useState([]);
  const [usageLogs, setUsageLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleBack = () => {
    if (onBack) return onBack();
    if (user?.role && priceListId) {
      const rolePrefix = user.role.toLowerCase();
      navigate(`/${rolePrefix}/price-lists/${priceListId}`);
    } else {
      navigate(-1);
    }
  };

  useEffect(() => {
    if (!priceListId) return;

    fetch(`${API_BASE_URL}/price-lists/${priceListId}/versions`)
      .then((res) => {
        if (!res.ok) throw new Error("Network response was not ok");
        return res.json();
      })
      .then((data) => {
        const versionList = Array.isArray(data) ? data : data?.data || [];
        setVersions(versionList);

        if (versionList.length > 0) {
          const firstId = versionList[0].id || versionList[0].version_id;
          setSelectedVersionId(firstId);
        }
      })
      .catch((err) => {
        console.error("Error fetching version history:", err);
        setVersions([]);
      });
  }, [priceListId]);

  useEffect(() => {
    if (!selectedVersionId) return;
    setLoading(true);

    if (activeTab === "details") {
      fetch(`${API_BASE_URL}/versions/${selectedVersionId}/details`)
        .then((res) => res.json())
        .then((data) => setVersionDetail(data))
        .catch((err) => console.error("Error fetching version details:", err))
        .finally(() => setLoading(false));
    } else if (activeTab === "changes") {
      fetch(`${API_BASE_URL}/versions/${selectedVersionId}/change-logs`)
        .then((res) => res.json())
        .then((data) => {
          const logs = Array.isArray(data) ? data : data?.data || [];
          setChangeLogs(logs);
        })
        .catch((err) => console.error("Error fetching change logs:", err))
        .finally(() => setLoading(false));
    } else if (activeTab === "usage") {
      fetch(`${API_BASE_URL}/versions/${selectedVersionId}/usage-logs`)
        .then((res) => res.json())
        .then((data) => {
          const logs = Array.isArray(data) ? data : data?.data || [];
          setUsageLogs(logs);
        })
        .catch((err) => console.error("Error fetching usage logs:", err))
        .finally(() => setLoading(false));
    }
  }, [selectedVersionId, activeTab]);

  const handleCheckboxChange = (vId) => {
    if (selectedVersionsForCompare.includes(vId)) {
      setSelectedVersionsForCompare(
        selectedVersionsForCompare.filter((id) => id !== vId)
      );
    } else if (selectedVersionsForCompare.length < 2) {
      setSelectedVersionsForCompare([...selectedVersionsForCompare, vId]);
    }
  };

  const renderStatusBadge = (status) => {
    const s = (status || "").toUpperCase();

    const statusStyles = {
      DRAFT: "bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]",
      EFFECTIVE: "bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]",
      SUPERSEDED: "bg-[#F8FAFC] text-[#475569] border-[#E2E8F0]",
      EXPIRED: "bg-[#F1F5F9] text-[#64748B] border-[#E2E8F0]",
      SUBMITTED: "bg-[#F0F9FF] text-[#0284C7] border-[#BAE6FD]",
      APPROVED: "bg-[#EFF6FF] text-[#2563EB] border-[#BFDBFE]",
      REJECTED: "bg-[#FEF2F2] text-[#DC2626] border-[#FECACA]",
    };

    const currentStyle =
      statusStyles[s] || "bg-slate-50 text-slate-500 border-slate-200";

    return (
      <span
        className={`px-2.5 py-0.5 rounded-md border text-[10px] font-bold tracking-wide uppercase inline-block ${currentStyle}`}
      >
        {s}
      </span>
    );
  };

  return (
    <div className="p-8 bg-[#F8FAFC] min-h-screen font-sans text-slate-700">
      {/* --- Top Header Action Bar --- */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2 bg-white rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-sm font-medium shadow-sm transition"
          >
            <ArrowLeft size={16} /> Quay lại
          </button>
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Xem lịch sử và chi tiết phiên bản
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Thông tin chi tiết cấu hình định mức đơn giá dịch vụ áp dụng.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button className="flex items-center gap-1.5 px-4 py-2 bg-[#508D83] hover:bg-[#43776E] text-white font-medium rounded-lg text-sm shadow-sm transition">
            <Plus size={16} /> Tạo phiên bản mới
          </button>
          <button
            disabled={selectedVersionsForCompare.length !== 2}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium text-sm transition border ${
              selectedVersionsForCompare.length === 2
                ? "bg-white text-slate-700 border-slate-300 shadow-sm cursor-pointer hover:bg-slate-50"
                : "bg-[#8CA2A0] text-white border-transparent cursor-not-allowed opacity-80"
            }`}
          >
            <RefreshCw size={15} /> So sánh ({selectedVersionsForCompare.length}/2)
          </button>
        </div>
      </div>

      {/* --- Main Grid Layout --- */}
      <div className="grid grid-cols-12 gap-6">
        {/* --- Cột Trái: Sidebar Lịch sử phiên bản --- */}
        <div className="col-span-12 lg:col-span-4 bg-white p-5 rounded-xl border border-slate-200/80 shadow-sm self-start">
          <div className="mb-4">
            <h2 className="font-bold text-slate-900 text-sm">Lịch sử phiên bản</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Tích chọn tối đa 2 bản để so sánh chênh lệch
            </p>
          </div>

          <div className="space-y-3">
            {Array.isArray(versions) && versions.length > 0 ? (
              versions.map((v) => {
                const currentId = v.id || v.version_id;
                const isSelected = selectedVersionId === currentId;
                const isChecked = selectedVersionsForCompare.includes(currentId);

                return (
                  <div
                    key={currentId || v.version_number}
                    // Bấm vào bất cứ vị trí nào trên Card để xem chi tiết
                    onClick={() => setSelectedVersionId(currentId)}
                    className={`p-4 rounded-xl border cursor-pointer transition relative ${
                      isSelected
                        ? "border-[#508D83] bg-[#F0FDF4]/30 ring-2 ring-[#508D83]"
                        : "border-slate-200/80 bg-white hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        {/* Checkbox ngắt lan truyền event để không ảnh hưởng đến card click */}
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleCheckboxChange(currentId);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="w-4 h-4 rounded text-[#508D83] focus:ring-[#508D83] border-slate-300 cursor-pointer"
                        />
                        <span className="font-bold text-slate-900 text-base">
                          {v.version_number}
                        </span>
                      </div>
                      {renderStatusBadge(v.status)}
                    </div>

                    <div className="text-xs text-slate-400 pl-7 flex items-center gap-1">
                      <span>
                        Hiệu lực từ:{" "}
                        <strong className="font-semibold text-slate-600">
                          {formatDate(v.valid_from)}
                        </strong>
                      </span>
                      <span className="ml-2">
                        Đến:{" "}
                        <strong className="font-semibold text-slate-600">
                          {formatDate(v.valid_to)}
                        </strong>
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="py-8 text-center text-xs text-slate-400">
                Không tìm thấy dữ liệu phiên bản
              </div>
            )}
          </div>
        </div>

        {/* --- Cột Phải: Nội dung chi tiết các Tabs --- */}
        <div className="col-span-12 lg:col-span-8 bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
          {/* Header Tabs Navigation */}
          <div className="flex border-b border-slate-100 px-6 pt-4 gap-8">
            <button
              onClick={() => setActiveTab("details")}
              className={`pb-3 text-sm font-semibold border-b-2 transition ${
                activeTab === "details"
                  ? "border-[#508D83] text-[#508D83]"
                  : "border-transparent text-slate-400 hover:text-slate-600"
              }`}
            >
              Đơn giá chi tiết
            </button>
            <button
              onClick={() => setActiveTab("changes")}
              className={`pb-3 text-sm font-semibold border-b-2 transition ${
                activeTab === "changes"
                  ? "border-[#508D83] text-[#508D83]"
                  : "border-transparent text-slate-400 hover:text-slate-600"
              }`}
            >
              Nhật ký thay đổi
            </button>
            <button
              onClick={() => setActiveTab("usage")}
              className={`pb-3 text-sm font-semibold border-b-2 transition ${
                activeTab === "usage"
                  ? "border-[#508D83] text-[#508D83]"
                  : "border-transparent text-slate-400 hover:text-slate-600"
              }`}
            >
              Lịch sử áp dụng
            </button>
          </div>

          {/* Body Content */}
          <div className="p-6">
            {/* === TAB 1: ĐƠN GIÁ CHI TIẾT === */}
            {activeTab === "details" &&
              (loading ? (
                <div className="py-12 text-center text-slate-400 text-sm">
                  Đang tải dữ liệu chi tiết...
                </div>
              ) : versionDetail ? (
                <div className="space-y-6">
                  {/* Block 1: Thông tin chung */}
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                      <span className="w-1 h-4 bg-[#508D83] rounded-sm"></span>
                      1. Thông tin chung bảng giá
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                          Mã bảng giá *
                        </label>
                        <input
                          type="text"
                          readOnly
                          value={versionDetail.price_list_code || ""}
                          className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-slate-200/80 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                          Tên bảng giá *
                        </label>
                        <input
                          type="text"
                          readOnly
                          value={versionDetail.price_list_name || ""}
                          className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-slate-200/80 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                          Đối tượng áp dụng cụ thể *
                        </label>
                        <input
                          type="text"
                          readOnly
                          value={
                            versionDetail.scope_id ||
                            versionDetail.scope_type ||
                            ""
                          }
                          className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-slate-200/80 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                          Thời gian hiệu lực *
                        </label>
                        <div className="relative">
                          <input
                            type="text"
                            readOnly
                            value={`${formatDate(versionDetail.valid_from)} đến ${formatDate(versionDetail.valid_to)}`}
                            className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-slate-200/80 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none"
                          />
                          <Calendar
                            size={15}
                            className="absolute right-3.5 top-3 text-slate-400"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Block 2: Cấu hình đơn giá */}
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                      <span className="w-1 h-4 bg-[#508D83] rounded-sm"></span>
                      2. Cấu hình đơn giá dịch vụ chi tiết
                    </h3>
                    <div className="border border-slate-200/80 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-[#F8FAFC] border-b border-slate-200/80 text-slate-600 font-bold">
                          <tr>
                            <th className="py-3 px-4">Dịch vụ cung cấp</th>
                            <th className="py-3 px-4">Mã dịch vụ</th>
                            <th className="py-3 px-4">Đơn vị</th>
                            <th className="py-3 px-4 text-right">
                              Đơn giá định mức
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {Array.isArray(versionDetail.items) &&
                            versionDetail.items.map((item) => (
                              <tr
                                key={item.service_item_id || item.service_code}
                                className="hover:bg-slate-50/50"
                              >
                                <td className="py-3.5 px-4 font-semibold text-slate-800">
                                  {item.service_name}
                                </td>
                                <td className="py-3.5 px-4 text-slate-400 text-xs">
                                  {item.service_code}
                                </td>
                                <td className="py-3.5 px-4 text-slate-500">
                                  {item.unit || "-"}
                                </td>
                                <td className="py-3.5 px-4 text-right font-bold text-slate-900">
                                  {item.unit_price?.toLocaleString("vi-VN")}{" "}
                                  <span className="text-[10px] font-normal text-slate-400 ml-0.5">
                                    VND
                                  </span>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="py-12 text-center text-slate-400 text-sm">
                  Vui lòng chọn một phiên bản để xem chi tiết
                </div>
              ))}

            {/* === TAB 2: NHẬT KÝ THAY ĐỔI === */}
            {activeTab === "changes" &&
              (loading ? (
                <div className="py-12 text-center text-slate-400 text-sm">
                  Đang tải nhật ký thay đổi...
                </div>
              ) : (
                <div className="space-y-4">
                  {changeLogs.length > 0 ? (
                    <div className="border border-slate-200/80 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-[#F8FAFC] border-b border-slate-200/80 text-slate-600 font-bold">
                          <tr>
                            <th className="py-3 px-4">Thời gian</th>
                            <th className="py-3 px-4">Người thực hiện</th>
                            <th className="py-3 px-4">Thao tác</th>
                            <th className="py-3 px-4">Chi tiết thay đổi</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {changeLogs.map((log, index) => (
                            <tr key={log.id || index}>
                              <td className="py-3 px-4 text-xs text-slate-500">
                                {formatDate(log.created_at || log.timestamp, true)}
                              </td>
                              <td className="py-3 px-4 font-semibold text-slate-700">
                                {log.performed_by || log.user_name}
                              </td>
                              <td className="py-3 px-4">
                                <span className="px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded font-medium">
                                  {log.action}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-xs text-slate-600">
                                {log.description || log.details}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="py-12 text-center">
                      <p className="text-slate-400 text-sm mb-3">
                        Không có nhật ký trực tiếp cho phiên bản này.
                      </p>
                      {onNavigateToChangeLogs && (
                        <button
                          onClick={() =>
                            selectedVersionId &&
                            onNavigateToChangeLogs(selectedVersionId)
                          }
                          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-[#508D83] font-semibold rounded-lg text-sm hover:bg-slate-50 transition"
                        >
                          <ExternalLink size={16} /> Đi đến trang Nhật ký thay đổi
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}

            {/* === TAB 3: LỊCH SỬ ÁP DỤNG === */}
            {activeTab === "usage" &&
              (loading ? (
                <div className="py-12 text-center text-slate-400 text-sm">
                  Đang tải lịch sử áp dụng...
                </div>
              ) : (
                <div className="space-y-4">
                  {usageLogs.length > 0 ? (
                    <div className="border border-slate-200/80 rounded-xl overflow-hidden">
                      <table className="w-full text-left text-sm">
                        <thead className="bg-[#F8FAFC] border-b border-slate-200/80 text-slate-600 font-bold">
                          <tr>
                            <th className="py-3 px-4">Mã bảng thanh toán</th>
                            <th className="py-3 px-4">Khách hàng / Đối tượng</th>
                            <th className="py-3 px-4">Ngày áp dụng</th>
                            <th className="py-3 px-4 text-right">Tổng tiền</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {usageLogs.map((log, index) => (
                            <tr key={log.id || index}>
                              <td className="py-3 px-4 font-mono text-xs font-semibold text-[#508D83]">
                                {log.payment_board_code || log.code}
                              </td>
                              <td className="py-3 px-4 text-slate-700">
                                {log.customer_name || log.target}
                              </td>
                              <td className="py-3 px-4 text-xs text-slate-500">
                                {formatDate(log.applied_at || log.date, true)}
                              </td>
                              <td className="py-3 px-4 text-right font-bold text-slate-900">
                                {log.total_amount?.toLocaleString("vi-VN")}{" "}
                                <span className="text-[10px] text-slate-400">VND</span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="py-12 text-center">
                      <p className="text-slate-400 text-sm mb-3">
                        Chưa có dữ liệu áp dụng cho phiên bản này.
                      </p>
                      {onNavigateToUsageLogs && (
                        <button
                          onClick={() =>
                            selectedVersionId &&
                            onNavigateToUsageLogs(selectedVersionId)
                          }
                          className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 text-[#508D83] font-semibold rounded-lg text-sm hover:bg-slate-50 transition"
                        >
                          <ExternalLink size={16} /> Đi đến trang Lịch sử áp dụng
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PriceListHistoryDetail;