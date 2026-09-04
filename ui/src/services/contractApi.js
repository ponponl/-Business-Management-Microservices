const BASE_URL = 'http://localhost:8080/api/v1';

const getHeaders = () => {
    const token = localStorage.getItem('token') || '';
    const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
    return {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userInfo.token || token}`,
    };
};

const buildMultipartFormData = (contractData, attachments = []) => {
    const formData = new FormData();
    formData.append('contract', JSON.stringify(contractData));
    if (Array.isArray(attachments)) {
        attachments.forEach((file) => {
            if (file) formData.append('attachments', file);
        });
    }
    return formData;
};

const CONTRACT_ERROR_MESSAGES = {
    APPROVAL_ALREADY_EXISTS: 'Hợp đồng đã có yêu cầu phê duyệt cho vòng hiện tại.',
    APPROVAL_ALREADY_PROCESSED: 'Yêu cầu phê duyệt này đã được xử lý.',
    APPROVAL_NOT_FOUND: 'Không tìm thấy yêu cầu phê duyệt phù hợp.',
    ATTACHMENT_NOT_FOUND: 'Không tìm thấy file đính kèm.',
    ATTACHMENT_FILE_NOT_FOUND: 'File đính kèm không còn tồn tại trên hệ thống.',
    CANCEL_NOT_ALLOWED: 'Không thể hủy hợp đồng ở trạng thái hiện tại.',
    COMMENT_REQUIRED: 'Vui lòng nhập lý do trước khi tiếp tục.',
    CONTRACT_NOT_FOUND: 'Không tìm thấy hợp đồng.',
    CURRENT_VERSION_NOT_FOUND: 'Không tìm thấy phiên bản hiện tại của hợp đồng.',
    CUSTOMER_INACTIVE: 'Khách hàng đang ngừng hoạt động.',
    CUSTOMER_NOT_FOUND: 'Không tìm thấy khách hàng đã chọn.',
    DUPLICATE_FILE_NAME: 'Có file đính kèm bị trùng tên.',
    EMPTY_FILE: 'File đính kèm không có nội dung.',
    FILE_EXTENSION_NOT_ALLOWED: 'Định dạng file đính kèm không được hỗ trợ.',
    FILE_TOO_LARGE: 'File đính kèm vượt quá dung lượng cho phép.',
    FILE_TYPE_NOT_ALLOWED: 'Loại file đính kèm không được hỗ trợ.',
    FORBIDDEN: 'Bạn không có quyền thực hiện thao tác này.',
    IDEMPOTENCY_KEY_REUSED: 'Yêu cầu gửi duyệt đã được sử dụng cho dữ liệu khác. Vui lòng thử lại.',
    INVALID_CONTRACT_JSON: 'Dữ liệu hợp đồng không hợp lệ.',
    INVALID_EFFECTIVE_PERIOD: 'Thời gian hiệu lực của hợp đồng không hợp lệ.',
    INVALID_FILE_NAME: 'Tên file đính kèm không hợp lệ.',
    INVALID_REVISION_CONTEXT: 'Thông tin vòng chỉnh sửa hiện tại không hợp lệ.',
    INVALID_REVISION_SOURCE: 'Không tìm thấy yêu cầu chỉnh sửa phù hợp từ Director.',
    INVALID_STATE: 'Không thể thực hiện thao tác ở trạng thái hợp đồng hiện tại.',
    MANAGER_APPROVAL_REQUIRED: 'Hợp đồng cần được Manager phê duyệt trước.',
    NOT_ASSIGNED_APPROVER: 'Bạn không phải người được phân công duyệt hợp đồng này.',
    REVISION_ALREADY_REQUESTED: 'Yêu cầu chỉnh sửa đã được tạo cho vòng duyệt hiện tại.',
    REVISION_ALREADY_SENT: 'Yêu cầu chỉnh sửa đã được gửi tới Staff.',
    REVISION_CONTEXT_NOT_FOUND: 'Không tìm thấy yêu cầu chỉnh sửa của vòng hiện tại.',
    REVISION_NOT_SENT_TO_STAFF: 'Manager chưa gửi yêu cầu chỉnh sửa tới Staff.',
    REVISION_UPDATE_REQUIRED: 'Vui lòng cập nhật hợp đồng trước khi gửi duyệt lại.',
    VERSION_CONFLICT: 'Hợp đồng vừa được thay đổi. Vui lòng tải lại và thử lại.',
};

const friendlyErrorMessage = (value, fallback = 'Có lỗi xảy ra. Vui lòng thử lại.') => {
    if (!value) return fallback;
    if (Array.isArray(value)) {
        const validationMessage = value.map((item) => item?.msg).filter(Boolean).join('; ');
        return validationMessage || fallback;
    }
    if (typeof value === 'object') {
        if (value.code && CONTRACT_ERROR_MESSAGES[value.code]) return CONTRACT_ERROR_MESSAGES[value.code];
        return friendlyErrorMessage(value.message || value.detail || value.code, fallback);
    }
    const message = String(value).trim();
    if (!message) return fallback;
    if (CONTRACT_ERROR_MESSAGES[message]) return CONTRACT_ERROR_MESSAGES[message];
    if (message === 'Failed to fetch') return 'Không thể kết nối đến Contract Service. Vui lòng thử lại.';
    if (/^[A-Z][A-Z0-9_]+$/.test(message)) return fallback;
    return message;
};

export const getContractErrorMessage = (error, fallback) => friendlyErrorMessage(error?.message || error, fallback);

const extractErrorMessage = async (response, fallback) => {
    try {
        const errorPayload = await response.json();
        return friendlyErrorMessage(errorPayload?.detail || errorPayload, fallback);
    } catch {
        return fallback || 'Có lỗi xảy ra. Vui lòng thử lại.';
    }
};

const throwResponseError = async (response, fallback) => {
    if (!response.ok) throw new Error(await extractErrorMessage(response, fallback));
};

export const fetchContracts = async ({ status = null, skip = 0, limit = 20, search = '', effectiveDate = '' } = {}) => {
    const url = new URL(`${BASE_URL}/contracts`);
    if (status) url.searchParams.append('status', status);
    url.searchParams.append('skip', skip);
    url.searchParams.append('limit', limit);
    if (search.trim()) url.searchParams.append('search', search.trim());
    if (effectiveDate) url.searchParams.append('effective_date', effectiveDate);
    const response = await fetch(url, { method: 'GET', headers: getHeaders() });
    await throwResponseError(response, 'Không thể tải danh sách hợp đồng.');
    return response.json();
};

export const fetchContractDetail = async (contractId) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}`, { method: 'GET', headers: getHeaders() });
    await throwResponseError(response, 'Không thể tải chi tiết hợp đồng.');
    return response.json();
};

export const createContract = async (data, attachments = []) => {
    const formData = buildMultipartFormData(data, attachments);
    const token = localStorage.getItem('token') || JSON.parse(localStorage.getItem('user_info') || '{}').token || '';
    const response = await fetch(`${BASE_URL}/contracts`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${token}` }, body: formData,
    });
    await throwResponseError(response, 'Không thể tạo hợp đồng.');
    return response.json();
};

export const updateContract = async (contractId, data, attachments = []) => {
    const formData = buildMultipartFormData(data, attachments);
    const token = localStorage.getItem('token') || JSON.parse(localStorage.getItem('user_info') || '{}').token || '';
    const response = await fetch(`${BASE_URL}/contracts/${contractId}`, {
        method: 'PUT', headers: { 'Authorization': `Bearer ${token}` }, body: formData,
    });
    await throwResponseError(response, 'Không thể cập nhật hợp đồng.');
    return response.json();
};

export const submitContract = async (contractId, idempotencyKey) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/submit`, {
        method: 'POST', headers: { ...getHeaders(), 'Idempotency-Key': idempotencyKey },
    });
    await throwResponseError(response, 'Không thể gửi hợp đồng để duyệt.');
    return response.json();
};

export const startContractReview = async (contractId) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/start-review`, {
        method: 'POST', headers: getHeaders(),
    });
    await throwResponseError(response, 'Không thể bắt đầu review hợp đồng.');
    return response.json();
};

const postApprovalAction = async (contractId, action, comment = null) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/${action}`, {
        method: 'POST', headers: getHeaders(), body: JSON.stringify({ comment }),
    });
    await throwResponseError(response, 'Không thể xử lý hợp đồng.');
    return response.json();
};

export const approveContract = (contractId, comment = null) => postApprovalAction(contractId, 'approve', comment);
export const requestContractRevision = (contractId, comment) => postApprovalAction(contractId, 'request-revision', comment);
export const rejectContract = (contractId, comment) => postApprovalAction(contractId, 'reject', comment);

export const sendRevisionToStaff = async (contractId, comment) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/send-revision`, {
        method: 'POST', headers: getHeaders(), body: JSON.stringify({ comment }),
    });
    await throwResponseError(response, 'Không thể gửi yêu cầu chỉnh sửa cho Staff.');
    return response.json();
};

export const cancelContract = async (contractId, reason) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/cancel`, {
        method: 'POST', headers: getHeaders(), body: JSON.stringify({ reason }),
    });
    await throwResponseError(response, 'Không thể hủy hợp đồng.');
    return response.json();
};

export const fetchCustomers = async (status = null) => {
    const url = new URL(`${BASE_URL}/customers`);
    if (status) url.searchParams.append('status', status);
    const response = await fetch(url, { method: 'GET', headers: getHeaders() });
    await throwResponseError(response, 'Không thể tải danh sách khách hàng.');
    return response.json();
};
