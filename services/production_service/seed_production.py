import os
import sys
from datetime import datetime, timedelta

# Cấu hình đường dẫn để import được module trong production_service
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import SessionLocal, Base, engine
from models.operation import OperationPeriod, OperationVolume, UnlockPeriodRequest, VolumeAuditLog, OperationOutboxEvent

# Đảm bảo các bảng đã được tạo
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    try:
        print("Đang xóa dữ liệu cũ (Production)...")
        db.query(UnlockPeriodRequest).delete()
        db.query(VolumeAuditLog).delete()
        db.query(OperationOutboxEvent).delete()
        db.query(OperationVolume).delete()
        db.query(OperationPeriod).delete()
        db.commit()

        print("Đang tạo kỳ sản lượng (Periods)...")
        # Kỳ quá khứ xa (Đã khóa)
        period_jul = OperationPeriod(
            period_key="2026-07",
            status="LOCKED",
            locked_at=datetime.utcnow() - timedelta(days=35),
            locked_by="manager_01",
            created_at=datetime.utcnow() - timedelta(days=60)
        )
        
        # Kỳ tháng trước (Đã khóa)
        period_aug = OperationPeriod(
            period_key="2026-08",
            status="LOCKED",
            locked_at=datetime.utcnow() - timedelta(days=2),
            locked_by="manager_01",
            created_at=datetime.utcnow() - timedelta(days=30)
        )
        
        # Kỳ hiện tại (Đang mở)
        period_sep = OperationPeriod(
            period_key="2026-09",
            status="OPEN",
            created_at=datetime.utcnow()
        )
        db.add_all([period_jul, period_aug, period_sep])
        db.commit()

        print("Đang tạo dữ liệu sản lượng (Volumes)...")
        volumes = [
            # Dữ liệu tháng 7 (Kỳ đã khóa)
            OperationVolume(
                contract_id="CTR-SEED-001",
                service_code="SRV-001",
                volume_date=datetime.utcnow() - timedelta(days=45),
                period_key="2026-07",
                quantity=200.0,
                unit="Container",
                recorded_by="staff_01",
                is_locked=True
            ),
            OperationVolume(
                contract_id="CTR-SEED-002",
                service_code="SRV-002",
                volume_date=datetime.utcnow() - timedelta(days=40),
                period_key="2026-07",
                quantity=100.0,
                unit="Chuyến",
                recorded_by="staff_02",
                is_locked=True
            ),
            OperationVolume(
                contract_id="CTR-SEED-003",
                service_code="SRV-003",
                volume_date=datetime.utcnow() - timedelta(days=38),
                period_key="2026-07",
                quantity=150.5,
                unit="Tấn",
                recorded_by="staff_01",
                is_locked=True
            ),
            # Dữ liệu tháng 8 (Kỳ đã khóa)
            OperationVolume(
                contract_id="CTR-SEED-001",
                service_code="SRV-001",
                volume_date=datetime.utcnow() - timedelta(days=15),
                period_key="2026-08",
                quantity=120.5,
                unit="Container",
                recorded_by="staff_01",
                is_locked=True
            ),
            OperationVolume(
                contract_id="CTR-SEED-002",
                service_code="SRV-002",
                volume_date=datetime.utcnow() - timedelta(days=10),
                period_key="2026-08",
                quantity=50.0,
                unit="Chuyến",
                recorded_by="staff_01",
                is_locked=True
            ),
            OperationVolume(
                contract_id="CTR-TEST-004",
                service_code="SRV-004",
                volume_date=datetime.utcnow() - timedelta(days=5),
                period_key="2026-08",
                quantity=88.8,
                unit="Khối",
                recorded_by="staff_02",
                is_locked=True
            ),
            # Dữ liệu tháng 9 (Kỳ đang mở)
            OperationVolume(
                contract_id="CTR-SEED-001",
                service_code="SRV-001",
                volume_date=datetime.utcnow() - timedelta(days=1),
                period_key="2026-09",
                quantity=45.0,
                unit="Container",
                recorded_by="staff_01",
                is_locked=False
            ),
            OperationVolume(
                contract_id="CTR-SEED-003",
                service_code="SRV-003",
                volume_date=datetime.utcnow(),
                period_key="2026-09",
                quantity=300.0,
                unit="Tấn",
                recorded_by="staff_02",
                is_locked=False
            ),
            OperationVolume(
                contract_id="CTR-SEED-001",
                service_code="SRV-004",
                volume_date=datetime.utcnow() - timedelta(hours=2),
                period_key="2026-09",
                quantity=12.0,
                unit="Khối",
                recorded_by="staff_03",
                is_locked=False
            )
        ]
        db.add_all(volumes)
        db.commit()

        print("Đang tạo dữ liệu yêu cầu mở khóa (Unlock Requests)...")
        # 1. Yêu cầu mở khóa nguyên cả kỳ 2026-08 (Đang chờ duyệt)
        req_period_pending = UnlockPeriodRequest(
            period_key="2026-08",
            requested_by="manager_01",
            reason="Khách hàng khiếu nại, cần mở lại kỳ để điều chỉnh toàn bộ.",
            status="PENDING",
            target_type="PERIOD"
        )
        
        # 2. Yêu cầu mở khóa nguyên cả kỳ 2026-07 (Đã bị từ chối)
        req_period_rejected = UnlockPeriodRequest(
            period_key="2026-07",
            requested_by="staff_01",
            reason="Xin mở lại tháng 7 để nhập sót 1 chuyến.",
            status="REJECTED",
            target_type="PERIOD",
            approved_by="director_01",
            approved_at=datetime.utcnow() - timedelta(days=20),
            reject_reason="Kỳ đã báo cáo tài chính, không thể mở lại."
        )

        # Lấy các dòng sản lượng tháng 8
        vols_aug = db.query(OperationVolume).filter(OperationVolume.period_key == "2026-08").all()
        
        # 3. Yêu cầu mở khóa 1 dòng sản lượng cụ thể (Đang chờ duyệt)
        req_volume_pending = UnlockPeriodRequest(
            period_key="2026-08",
            requested_by="staff_01",
            reason="Nhập sai số lượng container, cần sửa lại từ 120.5 thành 150.0.",
            status="PENDING",
            target_type="VOLUME",
            target_volume_id=vols_aug[0].id,
            target_service_code=vols_aug[0].service_code,
            old_quantity=vols_aug[0].quantity,
            proposed_quantity=150.0
        )
        
        # 4. Yêu cầu mở khóa 1 dòng sản lượng khác (Đã được duyệt)
        req_volume_approved = UnlockPeriodRequest(
            period_key="2026-08",
            requested_by="staff_02",
            reason="Khách hàng thay đổi số khối thực tế vào phút chót.",
            status="APPROVED",
            target_type="VOLUME",
            target_volume_id=vols_aug[1].id,
            target_service_code=vols_aug[1].service_code,
            old_quantity=vols_aug[1].quantity,
            proposed_quantity=75.0,
            approved_by="manager_01",
            approved_at=datetime.utcnow() - timedelta(days=1)
        )

        db.add_all([req_period_pending, req_period_rejected, req_volume_pending, req_volume_approved])
        db.commit()

        print("✅ Hoàn tất Seed dữ liệu cho Production Service!")

    except Exception as e:
        print(f"❌ Lỗi khi seed dữ liệu: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
