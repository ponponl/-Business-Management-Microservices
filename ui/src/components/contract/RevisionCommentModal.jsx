import React, { useState } from 'react';

export default function RevisionCommentModal({ title = 'Gửi yêu cầu chỉnh sửa', reason, onClose, onSubmit }) {
    const [comment, setComment] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async () => {
        if (!comment.trim()) {
            setError('Vui lòng nhập lý do chỉnh sửa.');
            return;
        }
        setLoading(true);
        setError('');
        try {
            await onSubmit(comment.trim());
        } catch (submitError) {
            setError(submitError.message || 'Không thể gửi yêu cầu chỉnh sửa.');
        } finally {
            setLoading(false);
        }
    };

    return <div className="processing-modal-backdrop" role="presentation"><div className="processing-modal" role="dialog" aria-modal="true"><div className="processing-modal-header"><h2>{title}</h2><button type="button" onClick={onClose} disabled={loading} aria-label="Đóng">×</button></div>{reason && <div className="processing-existing-reason"><strong>Lý do từ Director:</strong><p>{reason}</p></div>}<label className="processing-comment-label" htmlFor="revision-comment">Lý do của Manager (bắt buộc)</label><textarea id="revision-comment" value={comment} onChange={(event) => { setComment(event.target.value); setError(''); }} maxLength={2000} placeholder="Nhập lý do gửi yêu cầu chỉnh sửa cho Staff..." disabled={loading} />{error && <div className="processing-error" role="alert">{error}</div>}<div className="processing-modal-footer"><button className="processing-cancel" type="button" onClick={onClose} disabled={loading}>Hủy</button><button className="processing-confirm" type="button" onClick={handleSubmit} disabled={loading}>{loading ? 'Đang gửi...' : 'Xác nhận'}</button></div></div></div>;
}
