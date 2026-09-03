import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";

const API_BASE_URL = "http://localhost:8082/api/v1/price-history";

const formatDate = (dateString) => {
  if (!dateString || dateString === "---" || dateString === null) return "---";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    const day = String(date.getDate()).padStart(2, "0");
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const year = date.getFullYear();
    return `${year}-${month}-${day}`;
  } catch (error) {
    return dateString;
  }
};

const formatVersionNumber = (ver) => {
  if (ver === null || ver === undefined) return "1.0";
  const str = String(ver).trim();
  const cleanStr = str.replace(/^v+/i, "");
  return cleanStr || "1.0";
};

const renderStatusBadge = (status) => {
  const s = (status || "").toUpperCase();

  const statusStyles = {
    DRAFT: "bg-[#FFFBEB] text-[#D97706] border-[#FDE68A]",
    EFFECTIVE: "bg-[#ECFDF5] text-[#059669] border-[#A7F3D0]",
    SUPERSEDED: "bg-[#F3E8FF] text-[#7E22CE] border-[#E9D5FF]",
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

export const PriceVersionCompare = () => {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [versionList, setVersionList] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [compareData, setCompareData] = useState(null);

  useEffect(() => {
    const sId =
      location.state?.version1Id ||
      location.state?.sourceId ||
      searchParams.get("source") ||
      searchParams.get("source_version_id");

    const tId =
      location.state?.version2Id ||
      location.state?.targetId ||
      searchParams.get("target") ||
      searchParams.get("target_version_id");

    const initial = [];
    if (sId) initial.push(String(sId));
    if (tId) initial.push(String(tId));

    if (initial.length > 0) {
      setSelectedIds(initial);
    }
  }, [location.state, searchParams]);

  useEffect(() => {
    if (selectedIds.length !== 2) {
      setCompareData(null);
      setLoading(false);
      return;
    }

    const [id1, id2] = selectedIds;
    setLoading(true);

    fetch(
      `${API_BASE_URL}/versions/compare?source_version_id=${id1}&target_version_id=${id2}`
    )
      .then((res) => {
        if (!res.ok) throw new Error("Không thể tải dữ liệu so sánh");
        return res.json();
      })
      .then((data) => {
        const actualData = data?.data || data;
        setCompareData(actualData);
      })
      .catch((err) => {
        console.error("Lỗi khi tải dữ liệu so sánh:", err);
        setCompareData(null);
      })
      .finally(() => setLoading(false));
  }, [selectedIds]);

  const priceListId =
    compareData?.price_list_id ||
    location.state?.priceListId ||
    searchParams.get("price_list_id");

  useEffect(() => {
    const url = priceListId
      ? `${API_BASE_URL}/price-lists/${priceListId}/versions`
      : `${API_BASE_URL}/versions`;

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error("Lỗi API phiên bản");
        return res.json();
      })
      .then((data) => {
        const list =
          (Array.isArray(data) && data) ||
          (Array.isArray(data?.data) && data.data) ||
          (Array.isArray(data?.data?.items) && data.data.items) ||
          (Array.isArray(data?.items) && data.items) ||
          [];
        setVersionList(list);
      })
      .catch((err) => {
        console.warn("Chưa gọi được API danh sách phiên bản:", err);
        setVersionList([]);
      });
  }, [priceListId]);

  useEffect(() => {
    if (compareData && versionList.length === 0) {
      const fallbackList = [];
      if (compareData.source_version) {
        fallbackList.push({
          id: compareData.source_version.id || searchParams.get("source"),
          version_number:
            compareData.source_version.version_number ||
            compareData.source_version.version,
          status: compareData.source_version.status,
          valid_from:
            compareData.source_version.valid_from ||
            compareData.source_version.validFrom ||
            compareData.source_version.effective_from,
          valid_to:
            compareData.source_version.valid_to ||
            compareData.source_version.validTo ||
            compareData.source_version.effective_to,
          price_list_name:
            compareData.source_version.price_list_name ||
            compareData.source_version.price_name ||
            compareData.price_list_name,
        });
      }
      if (compareData.target_version) {
        fallbackList.push({
          id: compareData.target_version.id || searchParams.get("target"),
          version_number:
            compareData.target_version.version_number ||
            compareData.target_version.version,
          status: compareData.target_version.status,
          valid_from:
            compareData.target_version.valid_from ||
            compareData.target_version.validTo ||
            compareData.target_version.effective_from,
          valid_to:
            compareData.target_version.valid_to ||
            compareData.target_version.validTo ||
            compareData.target_version.effective_to,
          price_list_name:
            compareData.target_version.price_list_name ||
            compareData.target_version.price_name ||
            compareData.price_list_name,
        });
      }
      if (fallbackList.length > 0) {
        setVersionList(fallbackList);
      }
    }
  }, [compareData, versionList.length, searchParams]);

  const selectedVersionsOnly = versionList.filter((ver) =>
    selectedIds.includes(String(ver.id || ver.version_id))
  );

  const source_version = compareData?.source_version || {};
  const target_version = compareData?.target_version || {};
  const comparison_items =
    compareData?.comparison_items || compareData?.items || [];

  const rawSourceNum =
    source_version.version_number || source_version.version || "1.0";
  const rawTargetNum =
    target_version.version_number || target_version.version || "2.0";

  const sourceVerNum = formatVersionNumber(rawSourceNum);
  const targetVerNum = formatVersionNumber(rawTargetNum);

  const rawPriceName =
    compareData?.price_list_name ||
    compareData?.price_name ||
    source_version.price_list_name ||
    target_version.price_list_name ||
    "";
  const cleanPriceName = rawPriceName
    ? rawPriceName.replace(/\s*\([^)]*\)/g, "").trim()
    : "";

  const summary = (comparison_items || []).reduce(
    (acc, item) => {
      const diff = item.price_difference ?? item.difference ?? 0;
      const status = (item.status || "").toUpperCase();

      if (status === "INCREASED" || diff > 0) acc.increased += 1;
      else if (status === "DECREASED" || diff < 0) acc.decreased += 1;
      else acc.unchanged += 1;

      return acc;
    },
    { increased: 0, decreased: 0, unchanged: 0 }
  );

  return (
    <div className="bg-[#F8FAFC] min-h-screen p-6 font-sans text-slate-700 flex gap-6 items-start">
      {/* Sidebar Bên Trái - Chỉ hiện 2 phiên bản chọn so sánh */}
      <aside className="w-80 bg-white rounded-2xl border border-slate-200/80 p-5 flex flex-col shrink-0 shadow-sm">
        <h2 className="font-bold text-slate-900 text-sm">Lịch sử phiên bản</h2>
        <p className="text-xs text-slate-400 mt-0.5 mb-4">
          Tích chọn tối đa 2 bản để so sánh chênh lệch
        </p>

        <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-10rem)] pr-1">
          {selectedVersionsOnly.length === 0 ? (
            <div className="py-8 text-center text-xs text-slate-400">
              Chưa chọn phiên bản để so sánh
            </div>
          ) : (
            selectedVersionsOnly.map((ver) => {
              const verId = String(ver.id || ver.version_id);
              const rawVer = ver.version_number || ver.version || "1.0";
              const verNum = String(rawVer).toLowerCase().startsWith("v")
                ? rawVer
                : `v${rawVer}`;

              const itemVersionName =
                ver.price_list_name ||
                ver.price_name ||
                ver.version_price_name ||
                ver.priceName ||
                cleanPriceName ||
                "";

              const dateFrom =
                ver.valid_from ||
                ver.validFrom ||
                ver.effective_from ||
                ver.start_date;
              const dateTo =
                ver.valid_to ||
                ver.validTo ||
                ver.effective_to ||
                ver.end_date;

              return (
                <div
                  key={verId}
                  className="p-4 rounded-xl border border-[#508D83] bg-white ring-1 ring-[#508D83] relative"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-bold text-slate-900 text-base">
                      {verNum}
                    </span>
                    {renderStatusBadge(ver.status)}
                  </div>

                  {itemVersionName && (
                    <div className="text-xs font-semibold text-slate-700 mb-1 truncate">
                      {itemVersionName}
                    </div>
                  )}

                  <div className="text-xs text-slate-400 flex items-center gap-3">
                    <span>
                      Từ:{" "}
                      <strong className="font-semibold text-slate-600">
                        {formatDate(dateFrom)}
                      </strong>
                    </span>
                    <span>
                      Đến:{" "}
                      <strong className="font-semibold text-slate-600">
                        {formatDate(dateTo)}
                      </strong>
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* Nội dung So sánh Bên Phải */}
      <main className="flex-1 bg-white rounded-2xl border border-slate-200/80 p-8 shadow-sm flex flex-col justify-between min-h-[calc(100vh-3rem)]">
        <div>
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              So sánh đơn giá
            </h1>
            <button
              onClick={() => navigate(-1)}
              className="flex items-center gap-1.5 px-4 py-2 bg-white border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 font-medium text-sm transition cursor-pointer shadow-sm"
            >
              <ArrowLeft size={16} /> Thoát
            </button>
          </div>

          <div className="bg-slate-50/50 p-5 rounded-xl border border-slate-200/80 mb-6 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                Phạm vi đối chiếu
              </span>
              <h2 className="text-sm font-bold text-slate-800">
                Bảng so sánh chênh lệch đơn giá định mức{" "}
                {cleanPriceName && `(${cleanPriceName})`}
              </h2>
            </div>

            {selectedIds.length === 2 && (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-800 text-xs font-bold shadow-xs">
                  <span>v{targetVerNum}</span>
                  {target_version.status &&
                    renderStatusBadge(target_version.status)}
                </div>

                <span className="text-xs text-slate-400 font-bold">vs</span>

                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-800 text-xs font-bold shadow-xs">
                  <span>v{sourceVerNum}</span>
                  {source_version.status &&
                    renderStatusBadge(source_version.status)}
                </div>
              </div>
            )}
          </div>

          {loading ? (
            <div className="p-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
              Đang tải dữ liệu so sánh...
            </div>
          ) : selectedIds.length < 2 ? (
            <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
              Chưa có đủ thông tin phiên bản để tiến hành so sánh.
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200/80 overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-[#F8FAFC] border-b border-slate-200/80 text-slate-600 font-bold">
                  <tr>
                    <th className="py-3.5 px-6">Dịch vụ cung cấp</th>
                    <th className="py-3.5 px-4 text-right">
                      v{sourceVerNum} (Cũ)
                    </th>
                    <th className="py-3.5 px-4 text-right">
                      v{targetVerNum} (Mới)
                    </th>
                    <th className="py-3.5 px-6 text-right">Chênh lệch</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {comparison_items.length > 0 ? (
                    comparison_items.map((item, index) => {
                      const diff =
                        item.price_difference ?? item.difference ?? 0;
                      const pct =
                        item.percentage_change ?? item.percentage ?? null;

                      let diffColor = "text-slate-400";
                      let diffBadgeBg = "bg-slate-50 text-slate-500";
                      let prefix = "";

                      const status = (item.status || "").toUpperCase();

                      if (status === "INCREASED" || diff > 0) {
                        diffColor = "text-emerald-600";
                        diffBadgeBg = "bg-emerald-50 text-emerald-600";
                        prefix = "+";
                      } else if (status === "DECREASED" || diff < 0) {
                        diffColor = "text-rose-600";
                        diffBadgeBg = "bg-rose-50 text-rose-600";
                      }

                      return (
                        <tr
                          key={item.service_item_id || item.id || index}
                          className="hover:bg-slate-50/50"
                        >
                          <td className="py-4 px-6">
                            <div className="font-bold text-slate-800">
                              {item.service_name || item.name || "---"}
                            </div>
                            <div className="text-xs text-slate-400 mt-0.5 font-mono">
                              {item.service_code || item.code || "---"} •{" "}
                              {item.unit || "Lượt"}
                            </div>
                          </td>

                          <td className="py-4 px-4 text-right font-medium text-slate-600">
                            {item.old_price !== null &&
                            item.old_price !== undefined ? (
                              <>
                                {Number(item.old_price).toLocaleString("vi-VN")}{" "}
                                <span className="text-[10px] text-slate-400">
                                  VND
                                </span>
                              </>
                            ) : (
                              "---"
                            )}
                          </td>

                          <td className="py-4 px-4 text-right font-bold text-slate-900">
                            {item.new_price !== null &&
                            item.new_price !== undefined ? (
                              <>
                                {Number(item.new_price).toLocaleString("vi-VN")}{" "}
                                <span className="text-[10px] text-slate-400">
                                  VND
                                </span>
                              </>
                            ) : (
                              "---"
                            )}
                          </td>

                          <td className="py-4 px-6 text-right">
                            {diff !== null && diff !== 0 ? (
                              <div>
                                <div className={`font-bold ${diffColor}`}>
                                  {prefix}
                                  {Number(diff).toLocaleString("vi-VN")}{" "}
                                  <span className="text-[10px]">VND</span>
                                </div>
                                {pct !== null && (
                                  <span
                                    className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-bold mt-0.5 ${diffBadgeBg}`}
                                  >
                                    {prefix}
                                    {pct}%
                                  </span>
                                )}
                              </div>
                            ) : (
                              <span className="text-slate-400 font-bold">
                                —
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td
                        colSpan={4}
                        className="py-8 text-center text-xs text-slate-400"
                      >
                        Không có dữ liệu so sánh.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer Thống kê */}
        {selectedIds.length === 2 && !loading && (
          <div className="mt-8 pt-4 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600 font-medium">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>
                  Có <strong className="text-slate-900">{summary.increased}</strong>{" "}
                  dịch vụ điều chỉnh tăng
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
                <span>
                  Có <strong className="text-slate-900">{summary.decreased}</strong>{" "}
                  dịch vụ điều chỉnh giảm
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-slate-300"></span>
              <span>
                <strong className="text-slate-900">{summary.unchanged}</strong>{" "}
                dịch vụ giữ nguyên đơn giá định mức
              </span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default PriceVersionCompare;