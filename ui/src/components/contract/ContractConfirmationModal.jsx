import React, { useState } from 'react';
import { AlertTriangle, Send, X } from 'lucide-react';

export default function ContractConfirmationModal({ type, contractNumber, onClose, onConfirm }) {
    const [reason, setReason] = useState('');
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const isCancel = type === 'cancel';
    const Icon = isCancel ? AlertTriangle : Send;

    const handleSubmit = async (event) => {
        event.preventDefault();
        const normalizedReason = reason.trim();

        if (isCancel && !normalizedReason) {
            setError('Vui lòng nhập lý do hủy hợp đồng.');
            return;
        }

        setError('');
        setIsSubmitting(true);
        try {
            const succeeded = await onConfirm(normalizedReason);
            if (succeeded) onClose();
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="processing-modal-backdrop" role="presentation">
            <form className="processing-modal contract-confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="contract-confirmation-title" onSubmit={handleSubmit}>
                <div className="processing-modal-header">
                    <h2 id="contract-confirmation-title">{isCancel ? 'Hủy hợp đồng' : 'Gửi hợp đồng để duyệt'}</h2>
                    <button type="button" onClick={onClose} disabled={isSubmitting} aria-label="Đóng"><X size={19} /></button>
                </div>

                <div className={`contract-confirmation-icon ${isCancel ? 'is-cancel' : 'is-submit'}`}><Icon size={23} /></div>
                <p className="contract-confirmation-message">
                    {isCancel
                        ? <>Bạn có chắc chắn muốn hủy hợp đồng <strong>{contractNumber}</strong>?</>
                        : <>Bạn có chắc chắn muốn gửi hợp đồng <strong>{contractNumber}</strong> để Manager duyệt?</>}
                </p>

                {isCancel && (
                    <>
                        <label className="processing-comment-label" htmlFor="contract-cancel-reason">Lý do hủy <span>*</span></label>
                        <textarea
                            id="contract-cancel-reason"
                            value={reason}
                            onChange={(event) => { setReason(event.target.value); setError(''); }}
                            maxLength={2000}
                            placeholder="Nhập lý do hủy hợp đồng..."
                            disabled={isSubmitting}
                            autoFocus
                        />
                        <div className="processing-comment-count">{reason.length}/2000 ký tự</div>
                    </>
                )}

                {error && <div className="processing-error" role="alert">{error}</div>}
                <div className="processing-modal-footer">
                    <button className="processing-cancel" type="button" onClick={onClose} disabled={isSubmitting}>Hủy</button>
                    <button className={`processing-confirm ${isCancel ? 'is-danger' : ''}`} type="submit" disabled={isSubmitting}>
                        {isSubmitting ? 'Đang xử lý...' : 'Xác nhận'}
                    </button>
                </div>
            </form>
        </div>
    );
}
