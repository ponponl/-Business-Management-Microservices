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
      return `${day}-${month}-${year} ${hours}:${minutes}`;
    }

    return `${year}-${month}-${day}`;
  } catch (error) {
    return dateString;
  }
};

export const PriceListHistoryDetail = ({
  priceListId: propPriceListId,
  priceListCode: propPriceListCode,
  user,
  onBack,
  onNavigateToChangeLogs,
  onNavigateToUsageLogs,
  onCreateNewVersion,
}) => {
  const navigate = useNavigate();
  const params = useParams();

  const priceListIdentifier =
    propPriceListCode ||
    propPriceListId ||
    params.priceListCode ||
    params.priceListId ||
    params.id;

  const [versions, setVersions] = useState([]);
  const [selectedVersionId, setSelectedVersionId] = useState(null);
  const [selectedVersionsForCompare, setSelectedVersionsForCompare] = useState([]);

  const [activeTab, setActiveTab] = useState("details"); // 'details' | 'changes' | 'usage'

  const [versionDetail, setVersionDetail] = useState(null);
  const [changeLogs, setChangeLogs] = useState([]);
  const [hasUnreadChanges, setHasUnreadChanges] = useState(false);
  const [usageLogs, setUsageLogs] = useState([]);
  const [loading, setLoading] = useState(false);

  // Tìm phiên bản đang chọn từ danh sách Sidebar (bảng price_list_version)
  const selectedVersion = versions.find(
    (v) => (v.id || v.version_id) === selectedVersionId
  );

  // ÉP LẤY CHÍNH XÁC `price_list_name` TỪ PAYLOAD API DETAILS TRẢ VỀ TRƯỚC
  const displayPriceName =
    versionDetail?.price_list_name ||
    versionDetail?.price_name ||
    versionDetail?.version_price_name ||
    selectedVersion?.price_list_name ||
    selectedVersion?.price_name ||
    selectedVersion?.version_price_name ||
    selectedVersion?.priceName ||
    "";

  const isCreateVersionAllowed =
    (selectedVersion?.status || "").toUpperCase() === "EFFECTIVE";

  const handleBack = () => {
    if (onBack) return onBack();
    if (user?.role && priceListIdentifier) {
      const rolePrefix = user.role.toLowerCase();
      navigate(`/${rolePrefix}/price-lists/${priceListIdentifier}`);
    } else {
      navigate(-1);
    }
  };

  useEffect(() => {
    if (!priceListIdentifier) return;

    fetch(`${API_BASE_URL}/price-lists/${priceListIdentifier}/versions`)
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
  }, [priceListIdentifier]);

  useEffect(() => {
    if (!selectedVersionId) return;

    setLoading(true);
    setVersionDetail(null); // Clear cache cũ khi chuyển phiên bản

    const fetchDetails = fetch(`${API_BASE_URL}/versions/${selectedVersionId}/details`)
      .then((res) => res.json())
      .then((data) => {
        const detailData = data?.data || data;
        setVersionDetail(detailData);
      })
      .catch((err) => console.error("Error fetching version details:", err));

    const fetchChanges = fetch(`${API_BASE_URL}/versions/${selectedVersionId}/change-logs`)
      .then((res) => res.json())
      .then((data) => {
        const logs = Array.isArray(data) ? data : data?.data || [];
        setChangeLogs(logs);
        if (logs.length > 0 && activeTab !== "changes") {
          setHasUnreadChanges(true);
        }
      })
      .catch((err) => console.error("Error fetching change logs:", err));

    const fetchUsage = fetch(`${API_BASE_URL}/versions/${selectedVersionId}/usage-logs`)
      .then((res) => res.json())
      .then((data) => {
        const logs = Array.isArray(data) ? data : data?.data || [];
        setUsageLogs(logs);
      })
      .catch((err) => console.error("Error fetching usage logs:", err));

    Promise.all([fetchDetails, fetchChanges, fetchUsage]).finally(() => {
      setLoading(false);
    });
  }, [selectedVersionId]);

  const handleCheckboxChange = (vId) => {
    if (selectedVersionsForCompare.includes(vId)) {
      setSelectedVersionsForCompare(
        selectedVersionsForCompare.filter((id) => id !== vId)
      );
    } else if (selectedVersionsForCompare.length < 2) {
      setSelectedVersionsForCompare([...selectedVersionsForCompare, vId]);
    }
  };

  const handleCreateNewVersionClick = () => {
    if (!isCreateVersionAllowed) return;

    const currentVersionName = displayPriceName;

    const rawServices = versionDetail
      ? Array.isArray(versionDetail)
        ? versionDetail
        : versionDetail.items || versionDetail.services || versionDetail.details || []
      : [];

    const formattedServices = rawServices.map((item) => ({
      ...item,
      price: item.price ?? item.unit_price ?? item.unitPrice ?? 0,
      unit_price: item.unit_price ?? item.unitPrice ?? item.price ?? 0,
    }));

    const formattedPayload = {
      priceName: currentVersionName,
      targetType:
        selectedVersion?.target_type ||
        versionDetail?.target_type ||
        selectedVersion?.scope_type ||
        versionDetail?.scope_type ||
        "CUSTOMER",
      effectiveFrom:
        selectedVersion?.valid_from ||
        selectedVersion?.validFrom ||
        versionDetail?.valid_from ||
        new Date().toISOString(),
      effectiveTo:
        selectedVersion?.valid_to ||
        selectedVersion?.validTo ||
        versionDetail?.valid_to ||
        null,
      services: formattedServices,
    };

    if (onCreateNewVersion) {
      onCreateNewVersion({
        ...selectedVersion,
        ...formattedPayload,
        currentPriceName: currentVersionName,
        versionDetail: versionDetail,
      });
    } else {
      const targetId = priceListIdentifier || selectedVersionId;
      navigate(`/staff/price-lists/${targetId}/create-version`, {
        state: {
          parentVersion: selectedVersion,
          versionDetail: versionDetail,
          currentPriceName: currentVersionName,
          payloadData: formattedPayload,
        },
      });
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
        className={`px-2.5 py-0.5 rounded border text-[10px] font-bold tracking-wide uppercase inline-block ${currentStyle}`}
      >
        {s}
      </span>
    );
  };

  const renderScopeLabelAndValue = (detail) => {
    if (!detail) return { label: "Đối tượng áp dụng cụ thể *", value: "" };

    const type = (detail.scope_type || detail.target_type || "").toUpperCase();
    let label = "Đối tượng áp dụng cụ thể *";
    let value = detail.scope_name || detail.scope_id || detail.contract_id || detail.specific_target || "";

    if (type === "CUSTOMER" || detail.customer_code || detail.customer_name) {
      label = "Khách hàng áp dụng *";
      value = detail.customer_name
        ? `${detail.customer_name} (${detail.customer_code || detail.scope_id})`
        : detail.customer_code || value;
    } else if (type === "CONTRACT" || detail.contract_code || detail.contract_name || detail.contract_id) {
      label = "Số hợp đồng áp dụng *";
      value = detail.contract_code || detail.contract_name || detail.contract_id || value;
    }

    return { label, value };
  };

  const renderUsageStatusBadge = (status) => {
    const s = (status || "").toUpperCase();
    if (s.includes("SETTLED") || s.includes("ĐÃ QUYẾT TOÁN")) {
      return (
        <span className="px-2.5 py-0.5 rounded bg-[#E6F4EA] text-[#137333] text-xs font-semibold">
          Đã quyết toán
        </span>
      );
    }
    if (s.includes("PENDING") || s.includes("CHỜ QUYẾT TOÁN")) {
      return (
        <span className="px-2.5 py-0.5 rounded bg-[#FEF7E0] text-[#B06000] text-xs font-semibold">
          Chờ quyết toán
        </span>
      );
    }
    if (s.includes("OLD") || s.includes("GỐC CŨ")) {
      return (
        <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 text-xs font-semibold">
          Hóa đơn gốc cũ
        </span>
      );
    }
    return (
      <span className="px-2.5 py-0.5 rounded bg-slate-100 text-slate-600 text-xs font-semibold">
        {status || "Khác"}
      </span>
    );
  };

  const serviceItems = versionDetail
    ? Array.isArray(versionDetail)
      ? versionDetail
      : versionDetail.items || versionDetail.services || versionDetail.details || []
    : [];

  return (
    <div className="p-8 bg-[#F8FAFC] min-h-screen font-sans text-slate-700">
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
              Xem lịch sử và chi tiết bảng giá
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Thông tin chi tiết cấu hình định mức đơn giá dịch vụ áp dụng.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            disabled={!isCreateVersionAllowed}
            onClick={handleCreateNewVersionClick}
            title={
              !isCreateVersionAllowed
                ? "Chỉ có thể tạo phiên bản mới từ phiên bản đang áp dụng (EFFECTIVE)"
                : "Tạo phiên bản mới từ bản ghi này"
            }
            className={`flex items-center gap-1.5 px-4 py-2 font-medium rounded-lg text-sm transition ${
              isCreateVersionAllowed
                ? "bg-[#508D83] hover:bg-[#43776E] text-white shadow-sm cursor-pointer opacity-100"
                : "bg-[#508D83]/70 text-white cursor-not-allowed opacity-80"
            }`}
          >
            <Plus size={16} /> Tạo phiên bản mới
          </button>

          <button
            disabled={selectedVersionsForCompare.length !== 2}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium text-sm transition ${
              selectedVersionsForCompare.length === 2
                ? "bg-white text-slate-700 border border-slate-300 shadow-sm cursor-pointer hover:bg-slate-50"
                : "bg-[#7A9E9F] text-white cursor-not-allowed opacity-90"
            }`}
          >
            <RefreshCw size={15} /> So sánh ({selectedVersionsForCompare.length}/2)
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        {/* --- Cột Trái: Lịch sử phiên bản --- */}
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
                const rawVer = v.version_number || v.version || "1.0";
                const verNum = String(rawVer).toLowerCase().startsWith("v") ? rawVer : `v${rawVer}`;
                
                // Nếu item đang chọn trùng id với versionDetail thì ưu tiên dùng tên từ versionDetail
                const itemVersionName = isSelected && versionDetail?.price_list_name
                  ? versionDetail.price_list_name
                  : (v.price_list_name || v.price_name || "");

                return (
                  <div
                    key={currentId || v.version_number}
                    onClick={() => setSelectedVersionId(currentId)}
                    className={`p-4 rounded-xl border cursor-pointer transition relative ${
                      isSelected
                        ? "border-[#508D83] bg-white ring-1 ring-[#508D83]"
                        : "border-slate-200/80 bg-white hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
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
                          {verNum}
                        </span>
                      </div>
                      {renderStatusBadge(v.status)}
                    </div>

                    {itemVersionName && (
                      <div className="text-xs font-semibold text-slate-700 pl-7 mb-1 truncate">
                        {itemVersionName}
                      </div>
                    )}

                    <div className="text-xs text-slate-400 pl-7 flex items-center gap-3">
                      <span>
                        Từ:{" "}
                        <strong className="font-semibold text-slate-600">
                          {formatDate(v.valid_from || v.validFrom)}
                        </strong>
                      </span>
                      <span>
                        Đến:{" "}
                        <strong className="font-semibold text-slate-600">
                          {formatDate(v.valid_to || v.validTo)}
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

        {/* --- Cột Phải: Nội dung chi tiết --- */}
        <div className="col-span-12 lg:col-span-8 bg-white rounded-xl border border-slate-200/80 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between border-b border-slate-100 px-6 pt-4">
            <div className="flex gap-8">
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
                onClick={() => {
                  setActiveTab("changes");
                  setHasUnreadChanges(false);
                }}
                className={`pb-3 text-sm font-semibold border-b-2 transition relative ${
                  activeTab === "changes"
                    ? "border-[#508D83] text-[#508D83]"
                    : "border-transparent text-slate-400 hover:text-slate-600"
                }`}
              >
                Nhật ký thay đổi
                {hasUnreadChanges && changeLogs.length > 0 && (
                  <span className="absolute top-0 -right-2 w-2 h-2 bg-pink-500 rounded-full animate-pulse"></span>
                )}
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

            {activeTab === "usage" && (
              <div className="pb-3 text-xs text-slate-400">
                Hiển thị: <strong className="text-slate-700">{usageLogs.length} lượt áp dụng</strong>
              </div>
            )}
          </div>

          <div className="p-6">
            {/* === TAB 1: ĐƠN GIÁ CHI TIẾT === */}
            {activeTab === "details" &&
              (loading ? (
                <div className="py-12 text-center text-slate-400 text-sm">
                  Đang tải dữ liệu chi tiết...
                </div>
              ) : versionDetail ? (
                <div className="space-y-6">
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
                          value={
                            versionDetail.price_list_code ||
                            versionDetail.code ||
                            selectedVersion?.price_list_code ||
                            selectedVersion?.code ||
                            priceListIdentifier ||
                            ""
                          }
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
                          value={displayPriceName}
                          className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-slate-200/80 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none"
                        />
                      </div>
                      <div>
                        {(() => {
                          const { label, value } = renderScopeLabelAndValue(versionDetail);
                          return (
                            <>
                              <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                                {label}
                              </label>
                              <input
                                type="text"
                                readOnly
                                value={value}
                                className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-slate-200/80 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none"
                              />
                            </>
                          );
                        })()}
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-slate-500 mb-1.5">
                          Thời gian hiệu lực *
                        </label>
                        <div className="relative">
                          <input
                            type="text"
                            readOnly
                            value={`${formatDate(versionDetail.valid_from || selectedVersion?.valid_from || selectedVersion?.validFrom)} đến ${formatDate(versionDetail.valid_to || selectedVersion?.valid_to || selectedVersion?.validTo)}`}
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
                          {serviceItems.length > 0 ? (
                            serviceItems.map((item, idx) => {
                              const sName = item.service_name || item.serviceName || item.name || "---";
                              const sCode = item.service_code || item.serviceCode || item.code || "---";
                              const sUnit = item.unit || "Lượt";
                              const sPrice = item.unit_price !== undefined ? item.unit_price : (item.unitPrice !== undefined ? item.unitPrice : (item.price || 0));

                              return (
                                <tr
                                  key={item.service_item_id || item.serviceItemId || item.id || idx}
                                  className="hover:bg-slate-50/50"
                                >
                                  <td className="py-3.5 px-4 font-semibold text-slate-800">
                                    {sName}
                                  </td>
                                  <td className="py-3.5 px-4 text-slate-400 text-xs font-mono">
                                    {sCode}
                                  </td>
                                  <td className="py-3.5 px-4 text-slate-500">
                                    {sUnit}
                                  </td>
                                  <td className="py-3.5 px-4 text-right font-bold text-slate-900">
                                    {Number(sPrice).toLocaleString("vi-VN")}{" "}
                                    <span className="text-[10px] font-normal text-slate-400 ml-0.5">
                                      VND
                                    </span>
                                  </td>
                                </tr>
                              );
                            })
                          ) : (
                            <tr>
                              <td colSpan={4} className="py-8 text-center text-xs text-slate-400">
                                Chưa có dữ liệu hạng mục dịch vụ cho phiên bản này.
                              </td>
                            </tr>
                          )}
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
                <div className="relative pl-6 space-y-6 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-100">
                  {changeLogs.length > 0 ? (
                    changeLogs.map((log, index) => (
                      <div key={log.id || index} className="relative">
                        <div className="absolute -left-[23px] top-4 w-2.5 h-2.5 rounded-full bg-[#508D83] ring-4 ring-white"></div>

                        <div className="border border-slate-200/80 rounded-2xl p-5 bg-white shadow-sm">
                          <div className="flex items-center justify-between mb-4">
                            <span className="px-3 py-1 bg-[#EAF5F3] text-[#3B6E66] font-semibold text-xs rounded-lg inline-block">
                              {log.entity_name || log.field_name || "Tên bảng giá"}
                            </span>
                            <span className="text-xs text-slate-400">
                              {formatDate(log.changed_at || log.created_at, true)}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                              <p className="text-xs text-slate-400 mb-1">Giá trị cũ:</p>
                              <p className="text-sm font-semibold text-slate-600 line-through">
                                {log.old_value || "---"}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-400 mb-1">Giá trị mới:</p>
                              <p className="text-sm font-bold text-[#3B6E66]">
                                {log.new_value || "---"}
                              </p>
                            </div>
                          </div>

                          <div className="bg-[#F8FAFC] rounded-xl p-3 text-xs text-slate-600 mb-3">
                            <strong>Lý do:</strong> {log.change_reason || "Cập nhật thông tin phiên bản"}
                          </div>

                          <div className="text-right text-[11px] text-slate-400">
                            Thực hiện:{" "}
                            <span className="font-semibold text-slate-700">
                              {log.changed_by_name || log.performed_by || "Hệ thống"}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))
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
                <div className="relative pl-6 space-y-6 before:absolute before:left-[7px] before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-100">
                  {usageLogs.length > 0 ? (
                    usageLogs.map((log, index) => (
                      <div key={log.id || index} className="relative">
                        <div className="absolute -left-[23px] top-4 w-2.5 h-2.5 rounded-full bg-[#508D83] ring-4 ring-white"></div>

                        <div className="border border-slate-200/80 rounded-2xl p-5 bg-white shadow-sm">
                          <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-3">
                              <span className="px-3 py-1 bg-slate-100 text-slate-700 font-bold text-xs rounded-lg inline-block">
                                {log.payment_board_code || log.payment_board_id || log.code || "BSTATEMENT-2026-000"}
                              </span>
                              {renderUsageStatusBadge(log.status || "Đã quyết toán")}
                            </div>
                            <span className="text-xs text-slate-400">
                              {formatDate(log.applied_at || log.created_at || log.date, true)}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                              <p className="text-xs text-slate-400 mb-1">Khách hàng áp dụng</p>
                              <p className="text-sm font-bold text-slate-800">
                                {log.customer_name || log.customer_code || "---"}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-slate-400 mb-1">Số hợp đồng liên kết</p>
                              <p className="text-sm font-bold text-slate-800">
                                {log.contract_code || log.contract_number || "---"}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-end justify-between pt-2 border-t border-slate-50">
                            <div>
                              <p className="text-xs text-slate-400 mb-1">
                                {log.amount_type_label || "Giá trị quyết toán"}
                              </p>
                              <p className="text-lg font-bold text-slate-900">
                                {(log.total_amount || log.amount || 0).toLocaleString("vi-VN")}{" "}
                                <span className="text-xs font-normal text-slate-400">VND</span>
                              </p>
                            </div>
                            <div className="text-right text-xs text-slate-400">
                              {log.performed_by_label || "Người thực hiện quyết toán:"}{" "}
                              <span className="font-semibold text-slate-700 block mt-0.5">
                                {log.performed_by || log.created_by || "Trần Văn B (Kế toán bãi)"}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))
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