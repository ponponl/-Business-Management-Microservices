import React, { useEffect, useState, useRef } from "react";
import {
  Check,
  CheckCircle2,
  CreditCard,
  FilePlus2,
  Loader2,
  Pencil,
  RefreshCw,
  Search,
  Send,
  ShieldCheck,
  X,
  XCircle,
  Download,
  Users,
} from "lucide-react";

const API_BASE_URL = "http://localhost:8085/api/payments";
const API_CONTRACT_URL = "http://localhost:8080/api/v1/contracts";
const API_CUSTOMER_URL = "http://localhost:8080/api/v1/customers";
const API_PRICELIST_URL = "http://localhost:8080/api/v1/price-lists";
const API_VOLUMES_URL = "http://localhost:8080/api/v1/volumes";
const API_USERS_URL = "http://localhost:8080/api/v1/users";

const EMPTY_ITEM = {
  serviceCode: "",
  serviceName: "",
  unit: "container",
  quantity: 0,
  unitPrice: 0,
};
const STATUS_LABELS = {
  CALCULATED: "Đã tính",
  RECONCILED: "Đã đối soát",
  SUBMITTED: "Chờ duyệt",
  APPROVED: "Đã duyệt",
  REJECTED: "Từ chối",
  REVISION_REQUESTED: "Yêu cầu sửa",
  SIGNING: "Đang ký",
  SIGNED: "Đã ký",
  SIGN_FAILED: "Ký thất bại",
  ISSUED: "Đã phát hành",
};

const money = (value) => Number(value || 0).toLocaleString("vi-VN") + " đ";
const today = new Date().toISOString().slice(0, 10);

const authHeaders = (token) => {
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
};

// Helper: Fetch customers with search
const fetchCustomers = async (search = "", token) => {
  try {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    const response = await fetch(`${API_CUSTOMER_URL}?${params}`, {
      headers: authHeaders(token),
    });
    return (await response.json()) || [];
  } catch (err) {
    console.error("Fetch customers error:", err);
    return [];
  }
};

// Helper: Fetch contracts by customer
const fetchContracts = async (customerId, token) => {
  try {
    const params = new URLSearchParams({ customer_id: customerId, status: "Active" });
    const response = await fetch(`${API_CONTRACT_URL}?${params}`, {
      headers: authHeaders(token),
    });
    const data = await response.json();
    return data.items || data || [];
  } catch (err) {
    console.error("Fetch contracts error:", err);
    return [];
  }
};

// Helper: Find effective price table
const findEffectivePrice = async (periodStart, periodEnd, token) => {
  try {
    const response = await fetch(`${API_PRICELIST_URL}`, {
      headers: authHeaders(token),
    });
    const data = await response.json();
    const tables = data.items || data || [];
    const effective = tables.find(
      (t) =>
        t.status === "Effective" &&
        t.validFrom <= periodStart &&
        t.validTo >= periodEnd
    );
    return effective;
  } catch (err) {
    console.error("Fetch price tables error:", err);
    return null;
  }
};

// Helper: Fetch volumes
const fetchVolumes = async (customerId, contractId, periodStart, periodEnd, token) => {
  try {
    const params = new URLSearchParams({
      customer_id: customerId,
      contract_id: contractId,
      period_key: periodStart.slice(0, 7), // YYYY-MM
    });
    const response = await fetch(`${API_VOLUMES_URL}?${params}`, {
      headers: authHeaders(token),
    });
    const data = await response.json();
    return data.items || data || [];
  } catch (err) {
    console.error("Fetch volumes error:", err);
    return [];
  }
};

// Helper: Fetch users for assignee search
const fetchUsers = async (search = "", token) => {
  try {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    const response = await fetch(`${API_USERS_URL}?${params}`, {
      headers: authHeaders(token),
    });
    return (await response.json()) || [];
  } catch (err) {
    console.error("Fetch users error:", err);
    return [];
  }
};

function StatusBadge({ status }) {
  const colors = {
    CALCULATED: "bg-slate-100 text-slate-700",
    RECONCILED: "bg-cyan-100 text-cyan-700",
    SUBMITTED: "bg-amber-100 text-amber-700",
    APPROVED: "bg-blue-100 text-blue-700",
    REJECTED: "bg-rose-100 text-rose-700",
    REVISION_REQUESTED: "bg-orange-100 text-orange-700",
    SIGNING: "bg-violet-100 text-violet-700",
    SIGNED: "bg-emerald-100 text-emerald-700",
    SIGN_FAILED: "bg-rose-100 text-rose-700",
    ISSUED: "bg-emerald-100 text-emerald-700",
  };
  return (
    <span
      className={`rounded-md px-2 py-1 text-[10px] font-bold ${colors[status] || "bg-slate-100 text-slate-600"}`}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}

function PaymentEditor({ payment, user, onClose, onSaved }) {
  const token = user?.token || localStorage.getItem("token");
  const [form, setForm] = useState(
    payment || {
      customerId: "",
      contractId: "",
      priceTableId: "",
      periodStart: today.slice(0, 8) + "01",
      periodEnd: today,
      taxPercent: 10,
      items: [{ ...EMPTY_ITEM }],
    },
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  
  // Dropdowns & search states
  const [customers, setCustomers] = useState([]);
  const [customerSearch, setCustomerSearch] = useState("");
  const [showCustomerDropdown, setShowCustomerDropdown] = useState(false);
  
  const [contracts, setContracts] = useState([]);
  const [showContractDropdown, setShowContractDropdown] = useState(false);
  
  const [priceTableInfo, setPriceTableInfo] = useState(null);
  const [fetchingVolumes, setFetchingVolumes] = useState(false);

  const subtotal = form.items.reduce(
    (sum, item) =>
      sum + Number(item.quantity || 0) * Number(item.unitPrice || 0),
    0,
  );
  const total = subtotal * (1 + Number(form.taxPercent || 0) / 100);

  // Fetch customers on search
  useEffect(() => {
    const timer = setTimeout(async () => {
      const data = await fetchCustomers(customerSearch, token);
      setCustomers(data);
    }, 300);
    return () => clearTimeout(timer);
  }, [customerSearch, token]);

  // Fetch contracts when customer selected
  useEffect(() => {
    if (form.customerId) {
      (async () => {
        const data = await fetchContracts(form.customerId, token);
        setContracts(data);
      })();
    } else {
      setContracts([]);
      setForm((p) => ({ ...p, contractId: "" }));
    }
  }, [form.customerId, token]);

  // Auto-detect price table
  useEffect(() => {
    if (form.contractId && form.periodStart && form.periodEnd) {
      (async () => {
        const pt = await findEffectivePrice(form.periodStart, form.periodEnd, token);
        setPriceTableInfo(pt);
        setForm((p) => ({ ...p, priceTableId: pt?.priceCode || "" }));
      })();
    }
  }, [form.contractId, form.periodStart, form.periodEnd, token]);

  const update = (field, value) =>
    setForm((previous) => ({ ...previous, [field]: value }));
  
  const updateItem = (index, field, value) =>
    setForm((previous) => ({
      ...previous,
      items: previous.items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item,
      ),
    }));

  const handleFetchVolumes = async () => {
    if (!form.customerId || !form.contractId || !form.periodStart || !form.periodEnd) {
      setError("Vui lòng chọn khách hàng, hợp đồng và kỳ tính phí");
      return;
    }
    setFetchingVolumes(true);
    setError("");
    try {
      const volumes = await fetchVolumes(
        form.customerId,
        form.contractId,
        form.periodStart,
        form.periodEnd,
        token
      );
      if (volumes.length === 0) {
        setError("Không tìm thấy sản lượng cho kỳ này");
        setFetchingVolumes(false);
        return;
      }

      // Group volumes by service_code and aggregate
      const grouped = {};
      volumes.forEach((v) => {
        if (!grouped[v.service_code]) {
          grouped[v.service_code] = {
            serviceCode: v.service_code,
            serviceName: v.service_name || v.service_code,
            unit: v.unit || "container",
            quantity: 0,
            unitPrice: priceTableInfo?.details?.find(
              (d) => d.service_code === v.service_code
            )?.unit_price || 0,
          };
        }
        grouped[v.service_code].quantity += Number(v.quantity || 0);
      });

      setForm((p) => ({
        ...p,
        items: Object.values(grouped),
      }));
    } catch (err) {
      setError(`Lỗi khi lấy sản lượng: ${err.message}`);
    } finally {
      setFetchingVolumes(false);
    }
  };

  const save = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const response = await fetch(
        payment ? `${API_BASE_URL}/${payment.id}` : API_BASE_URL,
        {
          method: payment ? "PUT" : "POST",
          headers: authHeaders(token),
          body: JSON.stringify({
            ...form,
            items: form.items.map((item) => ({
              ...item,
              quantity: Number(item.quantity),
              unitPrice: Number(item.unitPrice),
            })),
          }),
        },
      );
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.detail || "Không thể lưu bảng thanh toán");
      onSaved(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-slate-900/40 p-4">
      <form
        onSubmit={save}
        className="max-h-[92vh] w-full max-w-4xl overflow-y-auto rounded-xl bg-white p-6 shadow-2xl"
      >
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-800">
              {payment ? "Chỉnh sửa bảng thanh toán" : "Lập bảng thanh toán"}
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Đơn giá được lưu thành snapshot tại thời điểm tính phí.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        {error && (
          <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
            {error}
          </div>
        )}
        
        {/* Header Inputs Row */}
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Customer Select */}
          <div className="relative text-xs font-medium text-slate-600">
            <label className="block mb-1">Khách hàng *</label>
            <div className="relative">
              <input
                type="text"
                placeholder="Tìm kiếm khách hàng..."
                value={showCustomerDropdown ? customerSearch : form.customerId}
                onChange={(e) => {
                  setCustomerSearch(e.target.value);
                  setShowCustomerDropdown(true);
                }}
                onFocus={() => setShowCustomerDropdown(true)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#2b727d]"
              />
              {showCustomerDropdown && customers.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-lg border border-slate-200 bg-white shadow-lg">
                  {customers.slice(0, 5).map((c) => (
                    <button
                      key={c.customer_id || c.id}
                      type="button"
                      onClick={() => {
                        update("customerId", c.customer_id || c.id);
                        setCustomerSearch("");
                        setShowCustomerDropdown(false);
                      }}
                      className="w-full px-3 py-2 text-left text-xs hover:bg-slate-50 border-b last:border-b-0"
                    >
                      <div className="font-semibold text-slate-800">
                        {c.customer_id || c.id}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {c.customer_name || c.name}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Contract Select */}
          <div className="text-xs font-medium text-slate-600">
            <label className="block mb-1">Hợp đồng (Active) *</label>
            <select
              required
              value={form.contractId}
              onChange={(e) => update("contractId", e.target.value)}
              disabled={!form.customerId}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#2b727d] disabled:bg-slate-50"
            >
              <option value="">-- Chọn hợp đồng --</option>
              {contracts.map((c) => (
                <option key={c.contract_id || c.id} value={c.contract_id || c.id}>
                  {c.contract_number || c.contract_id} - {c.contract_id}
                </option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <label className="text-xs font-medium text-slate-600">
            Từ ngày *
            <input
              required
              type="date"
              value={form.periodStart}
              onChange={(event) => update("periodStart", event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
          <label className="text-xs font-medium text-slate-600">
            Đến ngày *
            <input
              required
              type="date"
              value={form.periodEnd}
              onChange={(event) => update("periodEnd", event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>

          {/* Price Table - Read Only */}
          <div className="text-xs font-medium text-slate-600">
            <label className="block mb-1">Bảng giá (Effective) *</label>
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 font-semibold">
              {form.priceTableId || "-- Auto-detect --"}
            </div>
            {priceTableInfo && (
              <div className="mt-1 text-[11px] text-slate-500">
                Hiệu lực: {priceTableInfo.validFrom} - {priceTableInfo.validTo}
              </div>
            )}
          </div>

          {/* Tax Percent */}
          <label className="text-xs font-medium text-slate-600">
            Thuế VAT (%)
            <input
              type="number"
              min="0"
              max="100"
              value={form.taxPercent}
              onChange={(event) => update("taxPercent", event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            />
          </label>
        </div>

        {/* Fetch Volumes Button */}
        <div className="mt-5 flex items-center gap-2">
          <button
            type="button"
            onClick={handleFetchVolumes}
            disabled={fetchingVolumes || !form.customerId || !form.contractId}
            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
          >
            {fetchingVolumes ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            Lấy sản lượng kỳ này
          </button>
          <span className="text-xs text-slate-500">
            Dữ liệu từ Sản lượng Khai thác - Tự động tính thành tiền
          </span>
        </div>

        {/* Service Items Table */}
        <div className="mt-6 overflow-x-auto rounded-lg border border-slate-200">
          <table className="w-full min-w-[700px] text-left text-xs">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="p-3">Mã dịch vụ</th>
                <th className="p-3">Tên dịch vụ</th>
                <th className="p-3">ĐVT</th>
                <th className="p-3">Sản lượng</th>
                <th className="p-3">Đơn giá (Snapshot)</th>
                <th className="p-3 text-right">Thành tiền</th>
                <th className="p-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {form.items.map((item, index) => (
                <tr key={index}>
                  <td className="p-2">
                    <input
                      required
                      value={item.serviceCode}
                      onChange={(event) =>
                        updateItem(index, "serviceCode", event.target.value)
                      }
                      className="w-full rounded border border-slate-200 px-2 py-1.5 text-xs"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      required
                      value={item.serviceName}
                      onChange={(event) =>
                        updateItem(index, "serviceName", event.target.value)
                      }
                      className="w-full rounded border border-slate-200 px-2 py-1.5 text-xs"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      required
                      value={item.unit}
                      onChange={(event) =>
                        updateItem(index, "unit", event.target.value)
                      }
                      className="w-20 rounded border border-slate-200 px-2 py-1.5 text-xs"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      required
                      min="0"
                      type="number"
                      value={item.quantity}
                      onChange={(event) =>
                        updateItem(index, "quantity", event.target.value)
                      }
                      className="w-20 rounded border border-slate-200 px-2 py-1.5 text-xs"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      required
                      min="0"
                      type="number"
                      step="0.01"
                      value={item.unitPrice}
                      onChange={(event) =>
                        updateItem(index, "unitPrice", event.target.value)
                      }
                      className="w-24 rounded border border-slate-200 px-2 py-1.5 text-xs"
                    />
                  </td>
                  <td className="p-2 text-right font-semibold text-slate-800">
                    {money(Number(item.quantity || 0) * Number(item.unitPrice || 0))}
                  </td>
                  <td className="p-2">
                    <button
                      type="button"
                      disabled={form.items.length === 1}
                      onClick={() =>
                        setForm((previous) => ({
                          ...previous,
                          items: previous.items.filter(
                            (_, itemIndex) => itemIndex !== index,
                          ),
                        }))
                      }
                      className="rounded p-1.5 text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:opacity-30"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button
          type="button"
          onClick={() =>
            setForm((previous) => ({
              ...previous,
              items: [...previous.items, { ...EMPTY_ITEM }],
            }))
          }
          className="mt-3 text-xs font-semibold text-[#2b727d]"
        >
          + Thêm dòng dịch vụ
        </button>
        <label className="mt-4 block text-xs font-medium text-slate-600">
          Ghi chú
          <textarea
            value={form.note || ""}
            onChange={(event) => update("note", event.target.value)}
            rows="2"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
          />
        </label>
        <div className="mt-5 flex flex-col items-end gap-1 border-t border-slate-100 pt-4 text-sm">
          <span>
            Tạm tính: <b>{money(subtotal)}</b>
          </span>
          <span>
            VAT: <b>{money(total - subtotal)}</b>
          </span>
          <span className="text-base text-[#2b727d]">
            Tổng tiền: <b>{money(total)}</b>
          </span>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600"
          >
            Hủy
          </button>
          <button
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-[#2b727d] px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />} Lưu bảng
            thanh toán
          </button>
        </div>
      </form>
    </div>
  );
}

export default function PaymentManagementPage({ user }) {
  const role = user?.role || "STAFF";
  const token = user?.token || localStorage.getItem("token");
  const [payments, setPayments] = useState([]);
  const [stats, setStats] = useState({});
  const [selected, setSelected] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [editor, setEditor] = useState(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [actionDialog, setActionDialog] = useState(null);
  const [actionComment, setActionComment] = useState("");
  
  // Assignee selection dialog
  const [assigneeDialog, setAssigneeDialog] = useState(null);
  const [assigneeSearch, setAssigneeSearch] = useState("");
  const [availableAssignees, setAvailableAssignees] = useState([]);
  const [selectedAssignees, setSelectedAssignees] = useState([]);

  const load = async () => {
    setLoading(true);
    try {
      const [listResponse, statsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}?search=${encodeURIComponent(search)}`),
        fetch(`${API_BASE_URL}/stats`),
      ]);
      setPayments((await listResponse.json()).items || []);
      setStats(await statsResponse.json());
    } catch (err) {
      setMessage(`Không thể kết nối Payment Service: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [search]);

  useEffect(() => {
    if (selected?.id) {
      setWorkflowLoading(true);
      fetch(`${API_BASE_URL}/${selected.id}/workflow`, {
        headers: authHeaders(token),
      })
        .then((r) => r.json())
        .then((data) => setWorkflow(data))
        .catch(() => setWorkflow(null))
        .finally(() => setWorkflowLoading(false));
    } else {
      setWorkflow(null);
    }
  }, [selected?.id, token]);

  // Fetch assignees on search
  useEffect(() => {
    if (assigneeDialog && assigneeSearch) {
      const timer = setTimeout(async () => {
        const users = await fetchUsers(assigneeSearch, token);
        setAvailableAssignees(users);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [assigneeSearch, assigneeDialog, token]);

  const action = async (id, endpoint, comment = "", assignees = []) => {
    try {
      const headers = {
        ...authHeaders(token),
        "X-User": user?.username || role,
      };
      if (assignees.length) {
        headers["X-Approval-Assignees"] = assignees.join(",");
      }
      const response = await fetch(`${API_BASE_URL}/${id}/${endpoint}`, {
        method: "POST",
        headers,
        body: JSON.stringify({ comment }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Thao tác thất bại");
      setSelected(data);
      setMessage("Đã cập nhật trạng thái hồ sơ.");
      load();
    } catch (err) {
      setMessage(err.message);
    }
  };
  const openActionDialog = (id, endpoint) => {
    setActionComment("");
    setActionDialog({
      id,
      endpoint,
      title: endpoint === "reject" ? "Từ chối bảng thanh toán" : "Yêu cầu chỉnh sửa",
      description:
        endpoint === "reject"
          ? "Vui lòng nêu lý do từ chối hồ sơ này."
          : "Vui lòng nêu nội dung cần người lập chỉnh sửa.",
    });
  };

  const openAssigneeDialog = (paymentId) => {
    setAssigneeDialog({
      paymentId,
      title: "Chỉ định người duyệt"
    });
    setAssigneeSearch("");
    setSelectedAssignees([]);
    setAvailableAssignees([]);
  };

  const confirmAction = async (event) => {
    event.preventDefault();
    const comment = actionComment.trim();
    const { id, endpoint } = actionDialog;
    if (endpoint === "reject" && !comment) return;
    setActionDialog(null);
    setActionComment("");
    await action(id, endpoint, comment);
  };

  const confirmAssignees = async () => {
    if (!selectedAssignees.length) {
      setMessage("Vui lòng chọn ít nhất một người duyệt");
      return;
    }
    const { paymentId } = assigneeDialog;
    setAssigneeDialog(null);
    setSelectedAssignees([]);
    setAssigneeSearch("");
    await action(paymentId, "submit", "", selectedAssignees);
  };

  const canEdit =
    selected &&
    ["CALCULATED", "RECONCILED", "REVISION_REQUESTED"].includes(
      selected.status,
    );

  return (
    <div className="space-y-5 pb-10 text-slate-700">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 className="text-xl font-bold text-slate-800">
            Quản lý bảng thanh toán
          </h1>
          <p className="mt-1 text-xs text-slate-500">
            Lập, đối soát, phê duyệt và theo dõi ký điện tử hồ sơ thanh toán.
          </p>
        </div>
        {role === "STAFF" && (
          <button
            onClick={() => setEditor({})}
            className="flex items-center justify-center gap-2 rounded-lg bg-[#2b727d] px-4 py-2 text-xs font-semibold text-white"
          >
            <FilePlus2 className="h-4 w-4" /> Lập bảng thanh toán
          </button>
        )}
      </div>
      {message && (
        <div className="flex items-center justify-between rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-800">
          <span>{message}</span>
          <button onClick={() => setMessage("")}>
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {[
          ["total", "Tổng hồ sơ", CreditCard],
          ["draft", "Bản nháp", Pencil],
          ["submitted", "Chờ duyệt", ShieldCheck],
          ["approved", "Đã duyệt", CheckCircle2],
          ["signed", "Đã ký", Check],
        ].map(([key, label, Icon]) => (
          <div
            key={key}
            className="flex items-center justify-between rounded-xl border border-slate-200 bg-white p-4"
          >
            <div>
              <p className="text-[11px] text-slate-500">{label}</p>
              <p className="mt-1 text-xl font-bold text-slate-800">
                {stats[key] || 0}
              </p>
            </div>
            <Icon className="h-5 w-5 text-[#2b727d]" />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white p-3">
        <Search className="h-4 w-4 text-slate-400" />
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Tìm mã bảng, khách hàng hoặc hợp đồng..."
          className="w-full text-xs outline-none"
        />
        <button
          onClick={load}
          title="Làm mới"
          className="rounded p-1.5 text-slate-500 hover:bg-slate-100"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-left text-xs">
            <thead className="bg-slate-50 text-[11px] font-semibold text-slate-500">
              <tr>
                <th className="p-3">Mã bảng</th>
                <th className="p-3">Khách hàng / hợp đồng</th>
                <th className="p-3">Kỳ thanh toán</th>
                <th className="p-3">Tổng tiền</th>
                <th className="p-3">Người tạo</th>
                <th className="p-3">Trạng thái</th>
                <th className="p-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan="6" className="p-12 text-center">
                    <Loader2 className="mx-auto h-6 w-6 animate-spin text-[#2b727d]" />
                  </td>
                </tr>
              ) : payments.length ? (
                payments.map((payment) => (
                  <tr
                    key={payment.id}
                    onClick={() => setSelected(payment)}
                    className="cursor-pointer hover:bg-slate-50"
                  >
                    <td className="p-3 font-semibold text-slate-800">
                      {payment.code}
                    </td>
                    <td className="p-3">
                      <b>{payment.customerId}</b>
                      <div className="text-[10px] text-slate-400">
                        {payment.contractId} · {payment.priceTableId}
                      </div>
                    </td>
                    <td className="p-3 text-slate-500">
                      {payment.periodStart} đến {payment.periodEnd}
                    </td>
                    <td className="p-3 font-semibold">
                      {money(payment.totalAmount)}
                    </td>
                    <td className="p-3 text-slate-600">
                      <span className="text-[11px] font-semibold">
                        {payment.createdBy}
                      </span>
                    </td>
                    <td className="p-3">
                      <StatusBadge status={payment.status} />
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelected(payment);
                        }}
                        className="rounded p-1.5 text-slate-400 hover:bg-slate-100"
                        title="Xem chi tiết"
                      >
                        <CreditCard className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="6"
                    className="p-12 text-center text-xs text-slate-400"
                  >
                    Chưa có bảng thanh toán.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      {selected && (
        <div className="fixed inset-0 z-20 flex justify-end bg-slate-900/25">
          <section className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[11px] font-semibold text-slate-400">
                  CHI TIẾT BẢNG THANH TOÁN
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-800">
                  {selected.code}
                </h2>
              </div>
              <button
                onClick={() => setSelected(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 flex items-center justify-between">
              <StatusBadge status={selected.status} />
              <span className="text-xs text-slate-500">
                Trạng thái hồ sơ: {selected.status}
              </span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-400">Customer ID</span>
                <p className="font-semibold">{selected.customerId}</p>
              </div>
              <div>
                <span className="text-slate-400">Hợp đồng</span>
                <p className="font-semibold">{selected.contractId}</p>
              </div>
              <div>
                <span className="text-slate-400">Price table ID</span>
                <p className="font-semibold">{selected.priceTableId}</p>
              </div>
              <div>
                <span className="text-slate-400">Kỳ tính phí</span>
                <p className="font-semibold">
                  {selected.periodStart} - {selected.periodEnd}
                </p>
              </div>
            </div>
            <div className="mt-6 rounded-lg border border-slate-200">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500">
                  <tr>
                    <th className="p-2 text-left">Dịch vụ</th>
                    <th className="p-2 text-right">SL</th>
                    <th className="p-2 text-right">Đơn giá snapshot</th>
                    <th className="p-2 text-right">Thành tiền</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {selected.items?.map((item) => (
                    <tr key={item.id}>
                      <td className="p-2">
                        <b>{item.serviceName}</b>
                        <div className="text-[10px] text-slate-400">
                          {item.serviceCode} / {item.unit}
                        </div>
                      </td>
                      <td className="p-2 text-right">{item.quantity}</td>
                      <td className="p-2 text-right">
                        {money(item.unitPrice)}
                      </td>
                      <td className="p-2 text-right font-semibold">
                        {money(item.totalPrice)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 space-y-1 text-right text-sm">
              <p>Tạm tính: {money(selected.subTotal)}</p>
              <p>Thuế: {money(selected.taxAmount)}</p>
              <p className="text-base font-bold text-[#2b727d]">
                Tổng: {money(selected.totalAmount)}
              </p>
            </div>
            {workflow && workflow.steps && workflow.steps.length > 0 && (
              <div className="mt-6">
                <h3 className="mb-3 text-xs font-semibold uppercase text-slate-500">
                  Lịch sử phê duyệt
                </h3>
                <div className="overflow-x-auto rounded-lg border border-slate-200">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-50 text-slate-600">
                      <tr>
                        <th className="p-2 text-left">STT</th>
                        <th className="p-2 text-left">Người xử lý</th>
                        <th className="p-2 text-left">Trạng thái</th>
                        <th className="p-2 text-left">Lý do</th>
                        <th className="p-2 text-left">Thời gian</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {workflow.steps.map((step) => (
                        <tr key={step.stepNo}>
                          <td className="p-2 font-semibold text-slate-700">
                            {step.stepNo}
                          </td>
                          <td className="p-2 text-slate-600">{step.assigneeId}</td>
                          <td className="p-2">
                            <span
                              className={`rounded px-2 py-1 text-[10px] font-bold ${
                                step.status === "COMPLETED"
                                  ? step.action === "APPROVED"
                                    ? "bg-emerald-100 text-emerald-700"
                                    : "bg-rose-100 text-rose-700"
                                  : "bg-amber-100 text-amber-700"
                              }`}
                            >
                              {step.status === "PENDING"
                                ? "Chờ xử lý"
                                : step.action === "APPROVED"
                                  ? "Đã duyệt"
                                  : step.action === "REJECTED"
                                    ? "Từ chối"
                                    : "Yêu cầu sửa"}
                            </span>
                          </td>
                          <td className="p-2 text-slate-500">
                            {step.comment ? (
                              <span title={step.comment} className="truncate block">
                                {step.comment}
                              </span>
                            ) : (
                              <span className="text-slate-300">—</span>
                            )}
                          </td>
                          <td className="p-2 text-slate-500">
                            {step.completedAt
                              ? new Date(step.completedAt).toLocaleString("vi-VN")
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <div className="mt-6 flex flex-wrap justify-end gap-2">
              {role === "STAFF" && canEdit && (
                <>
                  <button
                    onClick={() => setEditor(selected)}
                    className="flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold"
                  >
                    <Pencil className="h-3.5 w-3.5" /> Sửa
                  </button>
                  <button
                    disabled={
                      selected.status !== "CALCULATED" &&
                      selected.status !== "REVISION_REQUESTED"
                    }
                    onClick={() => action(selected.id, "reconcile")}
                    className="flex items-center gap-1 rounded-lg bg-cyan-600 px-3 py-2 text-xs font-semibold text-white disabled:opacity-40"
                  >
                    <Check className="h-3.5 w-3.5" /> Đối soát
                  </button>
                </>
              )}
              {role === "STAFF" && selected.status === "RECONCILED" && (
                <button
                  onClick={() => openAssigneeDialog(selected.id)}
                  className="flex items-center gap-1 rounded-lg bg-[#2b727d] px-3 py-2 text-xs font-semibold text-white"
                >
                  <Send className="h-3.5 w-3.5" /> Gửi duyệt
                </button>
              )}
              {(role === "MANAGER" || role === "DIRECTOR") &&
                selected.status === "SUBMITTED" && (
                  <>
                    <button
                      onClick={() => openActionDialog(selected.id, "reject")}
                      className="flex items-center gap-1 rounded-lg border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700"
                    >
                      <XCircle className="h-3.5 w-3.5" /> Từ chối
                    </button>
                    <button
                      onClick={() =>
                        openActionDialog(selected.id, "request-revision")
                      }
                      className="flex items-center gap-1 rounded-lg border border-orange-200 px-3 py-2 text-xs font-semibold text-orange-700"
                    >
                      Yêu cầu sửa
                    </button>
                    <button
                      onClick={() => action(selected.id, "approve")}
                      className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" /> Phê duyệt
                    </button>
                  </>
                )}
              {role === "STAFF" && selected.status === "APPROVED" && (
                <button
                  onClick={() => action(selected.id, "send-sign")}
                  className="flex items-center gap-1 rounded-lg bg-violet-600 px-3 py-2 text-xs font-semibold text-white"
                >
                  <Send className="h-3.5 w-3.5" /> Gửi ký
                </button>
              )}
              {role === "STAFF" && selected.status === "SIGNING" && (
                <button
                  onClick={() => action(selected.id, "sign-callback")}
                  className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white"
                >
                  <Check className="h-3.5 w-3.5" /> Mô phỏng ký thành công
                </button>
              )}
            </div>
          </section>
        </div>
      )}
      {editor && (
        <PaymentEditor
          payment={editor.id ? editor : null}
          user={user}
          onClose={() => setEditor(null)}
          onSaved={(data) => {
            setEditor(null);
            setSelected(data);
            load();
          }}
        />
      )}
      {actionDialog && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/45 p-4">
          <form
            onSubmit={confirmAction}
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  Xử lý hồ sơ
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-800">
                  {actionDialog.title}
                </h2>
                <p className="mt-2 text-xs text-slate-500">
                  {actionDialog.description}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActionDialog(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"
                aria-label="Đóng"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <label className="mt-5 block text-xs font-semibold text-slate-700">
              Lý do <span className="text-rose-500">*</span>
              <textarea
                autoFocus
                required
                value={actionComment}
                onChange={(event) => setActionComment(event.target.value)}
                placeholder="Nhập lý do xử lý..."
                rows="4"
                className="mt-1 w-full resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm font-normal outline-none focus:border-[#2b727d] focus:ring-2 focus:ring-[#2b727d]/10"
              />
            </label>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setActionDialog(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Hủy
              </button>
              <button
                type="submit"
                disabled={actionDialog?.endpoint === "reject" && !actionComment.trim()}
                className={`rounded-lg px-4 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 ${actionDialog?.endpoint === "reject" ? "bg-rose-600 hover:bg-rose-700" : "bg-orange-500 hover:bg-orange-600"}`}
              >
                Xác nhận
              </button>
            </div>
          </form>
        </div>
      )}
      {assigneeDialog && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/45 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                  Workflow
                </p>
                <h2 className="mt-1 text-lg font-bold text-slate-800">
                  {assigneeDialog.title}
                </h2>
                <p className="mt-2 text-xs text-slate-500">
                  Chọn những người sẽ phê duyệt hồ sơ này (theo từng bước workflow)
                </p>
              </div>
              <button
                type="button"
                onClick={() => setAssigneeDialog(null)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-100"
                aria-label="Đóng"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            
            {/* Search Input */}
            <div className="mt-5 relative">
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Tìm kiếm người duyệt (nhập tên hoặc ID)
              </label>
              <input
                type="text"
                placeholder="Nhập tên hoặc ID..."
                value={assigneeSearch}
                onChange={(e) => setAssigneeSearch(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm outline-none focus:border-[#2b727d]"
              />
              {assigneeSearch && availableAssignees.length > 0 && (
                <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-lg border border-slate-200 bg-white shadow-lg max-h-40 overflow-y-auto">
                  {availableAssignees.slice(0, 5).map((user) => (
                    <button
                      key={user.user_id || user.id}
                      type="button"
                      onClick={() => {
                        const userId = user.user_id || user.id;
                        if (!selectedAssignees.includes(userId)) {
                          setSelectedAssignees([...selectedAssignees, userId]);
                        }
                        setAssigneeSearch("");
                        setAvailableAssignees([]);
                      }}
                      className="w-full px-3 py-2 text-left text-xs hover:bg-slate-50 border-b last:border-b-0"
                    >
                      <div className="font-semibold text-slate-800">
                        {user.username || user.name}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {user.user_id || user.id} · {user.role}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Selected Assignees */}
            {selectedAssignees.length > 0 && (
              <div className="mt-4 space-y-2">
                <label className="block text-xs font-semibold text-slate-700">
                  Người được chỉ định ({selectedAssignees.length})
                </label>
                <div className="space-y-1">
                  {selectedAssignees.map((id, idx) => (
                    <div
                      key={id}
                      className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs"
                    >
                      <div>
                        <span className="font-semibold text-slate-700">Bước {idx + 1}:</span>
                        <span className="ml-2 text-slate-600">{id}</span>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          setSelectedAssignees(
                            selectedAssignees.filter((_, i) => i !== idx)
                          )
                        }
                        className="text-slate-400 hover:text-rose-600"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAssigneeDialog(null)}
                className="rounded-lg border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-50"
              >
                Hủy
              </button>
              <button
                type="button"
                onClick={confirmAssignees}
                disabled={!selectedAssignees.length}
                className="rounded-lg bg-[#2b727d] px-4 py-2 text-xs font-semibold text-white disabled:opacity-50"
              >
                <Users className="inline h-3.5 w-3.5 mr-1" />
                Xác nhận ({selectedAssignees.length})
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
