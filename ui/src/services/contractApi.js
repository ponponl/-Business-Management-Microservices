const BASE_URL = 'http://localhost:8080/api/v1';

const getHeaders = () => {
    const token = localStorage.getItem('token') || ''; // Adjust if token is stored differently
    // Actually, in this project, they might store token in user_info. Let's check App.jsx.
    // user_info = { name, username, role, token }
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
            if (file) {
                formData.append('attachments', file);
            }
        });
    }

    return formData;
};

const extractErrorMessage = async (response) => {
    try {
        const errorPayload = await response.json();
        if (errorPayload?.detail) {
            if (typeof errorPayload.detail === 'string') {
                return errorPayload.detail;
            }
            if (typeof errorPayload.detail === 'object') {
                return errorPayload.detail.message || errorPayload.detail.code || 'Có lỗi xảy ra';
            }
        }
        return 'Có lỗi xảy ra';
    } catch {
        return 'Có lỗi xảy ra';
    }
};

export const fetchContracts = async (status = null) => {
    const url = new URL(`${BASE_URL}/contracts`);
    if (status) url.searchParams.append('status', status);
    // You can also append skip, limit, customer_id if needed
    
    const response = await fetch(url, {
        method: 'GET',
        headers: getHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch contracts');
    return response.json();
};

export const fetchContractDetail = async (contractId) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}`, {
        method: 'GET',
        headers: getHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch contract details');
    return response.json();
};

export const createContract = async (data, attachments = []) => {
    const formData = buildMultipartFormData(data, attachments);
    const token = localStorage.getItem('token') || JSON.parse(localStorage.getItem('user_info') || '{}').token || '';

    const response = await fetch(`${BASE_URL}/contracts`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
        },
        body: formData,
    });
    if (!response.ok) {
        const message = await extractErrorMessage(response);
        throw new Error(message || 'Failed to create contract');
    }
    return response.json();
};

export const updateContract = async (contractId, data, attachments = []) => {
    const formData = buildMultipartFormData(data, attachments);
    const token = localStorage.getItem('token') || JSON.parse(localStorage.getItem('user_info') || '{}').token || '';

    const response = await fetch(`${BASE_URL}/contracts/${contractId}`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`,
        },
        body: formData,
    });
    if (!response.ok) {
        const message = await extractErrorMessage(response);
        throw new Error(message || 'Failed to update contract');
    }
    return response.json();
};

export const submitContract = async (contractId, idempotencyKey) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/submit`, {
        method: 'POST',
        headers: {
            ...getHeaders(),
            'Idempotency-Key': idempotencyKey,
        },
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to submit contract');
    }
    return response.json();
};

export const cancelContract = async (contractId, reason) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}/cancel`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ reason }),
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to cancel contract');
    }
    return response.json();
};

export const fetchCustomers = async (status = null) => {
    const url = new URL(`${BASE_URL}/customers`);
    if (status) url.searchParams.append('status', status);
    
    const response = await fetch(url, {
        method: 'GET',
        headers: getHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch customers');
    return response.json();
};
