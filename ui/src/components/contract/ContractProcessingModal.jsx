import React, { useState } from 'react';
import { Check, CheckCircle2, Edit3, X, XCircle } from 'lucide-react';
import { useToast } from '../common/ToastContext';
import { approveContract, getContractErrorMessage, rejectContract, requestContractRevision } from '../../services/contractApi';

const ACTIONS = {
    approve: {
        title: 'Phê duyệt',
        description: 'Chuyển hợp đồng sang bước tiếp theo',
        className: 'approve',
        icon: CheckCircle2,
    },
    revision: {
        title: 'Yêu cầu chỉnh sửa',
        description: 'Yêu cầu chỉnh sửa và gửi lại cho Staff',
        className: 'revision',
        icon: Edit3,
    },
    reject: {
        title: 'Từ chối',
        description: 'Từ chối hợp đồng và gửi lại cho Staff',
        className: 'reject',
        icon: XCircle,
    },
};

const formatMoney = (value) => new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value || 0);

export default function ContractProcessingModal({ contract, customerName, role = 'MANAGER', approvalStatus = 'PENDING', onClose, onSuccess }) {
    const toast = useToast();
    const [selectedAction, setSelectedAction] = useState('approve');
    const [comment, setComment] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');

    if (!contract) return null;

    const isCommentRequired = selectedAction !== 'approve';
    const isRevisionRequested = approvalStatus === 'REVISION_REQUESTED';

    const handleSubmit = async () => {
        if (isCommentRequired && !comment.trim()) {
            setError('Vui lòng nhập nhận xét trước khi tiếp tục.');
            toast.error('Vui lòng nhập nhận xét trước khi tiếp tục.');
            return;
        }

        setError('');
        setIsSubmitting(true);
        try {
            let response;
            if (selectedAction === 'approve') response = await approveContract(contract.contract_id, comment.trim() || null);
            if (selectedAction === 'revision') response = await requestContractRevision(contract.contract_id, comment.trim());
            if (selectedAction === 'reject') response = await rejectContract(contract.contract_id, comment.trim());
            const successMessages = {
                approve: 'Phê duyệt hợp đồng thành công.',
                revision: 'Đã gửi yêu cầu chỉnh sửa hợp đồng.',
                reject: 'Đã từ chối hợp đồng.',
            };
            toast.success(successMessages[selectedAction]);
            await onSuccess(response);
        } catch (submitError) {
            const message = getContractErrorMessage(submitError, 'Không thể xử lý hợp đồng.');
            setError(message);
            toast.error(message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return <div className="processing-modal-backdrop" role="presentation">
        <div className="processing-modal" role="dialog" aria-modal="true" aria-labelledby="processing-modal-title">
            <div className="processing-modal-header"><h2 id="processing-modal-title">Xử lý hợp đồng</h2><button type="button" onClick={onClose} disabled={isSubmitting} aria-label="Đóng"><X size={19} /></button></div>
            <div className="processing-contract-summary"><p><span>Mã hợp đồng:</span> <strong>{contract.contract_number}</strong></p><p><span>Khách hàng:</span> <strong>{customerName}</strong></p><p><span>Giá trị:</span> <strong>{formatMoney(contract.contract_value)}</strong></p></div>
            <div className="processing-divider" />
            {isRevisionRequested ? <div className="processing-revision-status"><strong>Đã yêu cầu chỉnh sửa</strong><span>Đang chờ Manager xử lý</span></div> : <p className="processing-question">Bạn muốn thực hiện hành động gì với hợp đồng này?</p>}
            {!isRevisionRequested && <div className="processing-actions">{Object.entries(ACTIONS).map(([key, item]) => { const Icon = item.icon; const description = key === 'approve' && role === 'MANAGER' ? 'Chuyển hợp đồng sang bước Director review' : item.description; return <button key={key} type="button" className={`processing-action ${item.className} ${selectedAction === key ? 'selected' : ''}`} onClick={() => { setSelectedAction(key); setError(''); }} disabled={isSubmitting}><span className="processing-action-icon"><Icon size={19} /></span><span><strong>{item.title}</strong><small>{description}</small></span><Check size={17} className="processing-selected-check" /></button>; })}</div>}
            {!isRevisionRequested && <><label className="processing-comment-label" htmlFor="processing-comment">Nhận xét {isCommentRequired ? '(bắt buộc nếu chọn yêu cầu chỉnh sửa hoặc từ chối)' : '(không bắt buộc)'}</label><textarea id="processing-comment" value={comment} onChange={(event) => setComment(event.target.value)} maxLength={2000} placeholder="Nhập nhận xét của bạn..." disabled={isSubmitting} /><div className="processing-comment-count">{comment.length}/2000 ký tự</div></>}
            {error && <div className="processing-error" role="alert">{error}</div>}
            <div className="processing-modal-footer"><button className="processing-cancel" type="button" onClick={onClose} disabled={isSubmitting}>{isRevisionRequested ? 'Đóng' : 'Hủy'}</button>{!isRevisionRequested && <button className="processing-confirm" type="button" onClick={handleSubmit} disabled={isSubmitting}>{isSubmitting ? 'Đang xử lý...' : 'Xác nhận'}</button>}</div>
        </div>
    </div>;
}
