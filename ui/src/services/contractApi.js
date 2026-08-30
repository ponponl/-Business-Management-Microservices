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

export const createContract = async (data) => {
    const response = await fetch(`${BASE_URL}/contracts`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to create contract');
    }
    return response.json();
};

export const updateContract = async (contractId, data) => {
    const response = await fetch(`${BASE_URL}/contracts/${contractId}`, {
        method: 'PUT',
        headers: getHeaders(),
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Failed to update contract');
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
