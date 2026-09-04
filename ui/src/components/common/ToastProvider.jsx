import React, { useCallback, useMemo, useState } from 'react';
import { CheckCircle2, CircleAlert, X } from 'lucide-react';
import { ToastContext } from './ToastContext';
let nextToastId = 0;

function Toast({ toast, onClose }) {
    const Icon = toast.type === 'success' ? CheckCircle2 : CircleAlert;

    React.useEffect(() => {
        const timer = window.setTimeout(() => onClose(toast.id), toast.duration);
        return () => window.clearTimeout(timer);
    }, [onClose, toast.duration, toast.id]);

    return (
        <div className={`app-toast app-toast-${toast.type}`} role={toast.type === 'error' ? 'alert' : 'status'}>
            <Icon className="app-toast-icon" size={20} aria-hidden="true" />
            <div className="app-toast-content">
                <strong>{toast.type === 'success' ? 'Thành công' : 'Có lỗi xảy ra'}</strong>
                <p>{toast.message}</p>
            </div>
            <button type="button" onClick={() => onClose(toast.id)} aria-label="Đóng thông báo">
                <X size={17} />
            </button>
        </div>
    );
}

export function ToastProvider({ children }) {
    const [toasts, setToasts] = useState([]);

    const removeToast = useCallback((id) => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
    }, []);

    const notify = useCallback((type, message, duration = 4500) => {
        if (!message) return;

        setToasts((current) => {
            const duplicate = current.some((toast) => toast.type === type && toast.message === message);
            if (duplicate) return current;

            nextToastId += 1;
            return [...current, { id: nextToastId, type, message, duration }];
        });
    }, []);

    const value = useMemo(() => ({
        success: (message, duration) => notify('success', message, duration),
        error: (message, duration) => notify('error', message, duration),
    }), [notify]);

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className="app-toast-viewport" aria-live="polite" aria-atomic="false">
                {toasts.map((toast) => <Toast key={toast.id} toast={toast} onClose={removeToast} />)}
            </div>
        </ToastContext.Provider>
    );
}
