import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from models.database import Base, SessionLocal, engine
from models.payment import (
    PaymentBoard,
    PaymentDetail,
    PaymentWorkflow,
    PaymentWorkflowStep,
)


def seed_payments():
    print("1. Đang drop và re-create bảng...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("2. Đang tạo mock payment data...")

        # Define some test users
        staff_id = "staff01"
        manager_id = "manager01"
        director_id = "director01"

        # Mock Payment 1: CALCULATED (draft)
        payment1 = PaymentBoard(
            id=str(uuid.uuid4()),
            code="PAY-DEMO-001",
            customer_id="CUS001",
            contract_id="CTR-SEED-001",
            price_table_id="PL-2026-001",
            period_start="2026-08-01",
            period_end="2026-08-31",
            sub_total=Decimal("48923000.00"),
            tax_percent=Decimal("10.00"),
            tax_amount=Decimal("4892300.00"),
            total_amount=Decimal("53815300.00"),
            status="CALCULATED",
            created_by=staff_id,
            created_at=datetime.utcnow(),
        )
        db.add(payment1)
        db.flush()

        # Add line items for payment1
        detail1 = PaymentDetail(
            id=str(uuid.uuid4()),
            payment_board_id=payment1.id,
            service_code="SRV-20ft-IN",
            service_name="Bốc xếp container 20ft (Hàng nhập)",
            unit="Container",
            quantity=Decimal("120.50"),
            unit_price=Decimal("406000.00"),
            total_price=Decimal("48923000.00"),
        )
        db.add(detail1)

        # Mock Payment 2: SUBMITTED (waiting for manager approval)
        payment2 = PaymentBoard(
            id=str(uuid.uuid4()),
            code="PAY-DEMO-002",
            customer_id="CUS001",
            contract_id="CTR-SEED-002",
            price_table_id="PL-2026-003",
            period_start="2026-08-01",
            period_end="2026-08-31",
            sub_total=Decimal("2610000.00"),
            tax_percent=Decimal("10.00"),
            tax_amount=Decimal("261000.00"),
            total_amount=Decimal("2871000.00"),
            status="SUBMITTED",
            created_by=staff_id,
            created_at=datetime.utcnow() - timedelta(hours=2),
        )
        db.add(payment2)
        db.flush()

        detail2 = PaymentDetail(
            id=str(uuid.uuid4()),
            payment_board_id=payment2.id,
            service_code="SRV-WH-GEN",
            service_name="Lưu kho bãi tổng hợp",
            unit="Chuyến",
            quantity=Decimal("50.00"),
            unit_price=Decimal("52200.00"),
            total_price=Decimal("2610000.00"),
        )
        db.add(detail2)

        # Workflow for payment2
        workflow2 = PaymentWorkflow(
            id=str(uuid.uuid4()),
            payment_board_id=payment2.id,
            current_step=1,
            status="IN_PROGRESS",
        )
        db.add(workflow2)
        db.flush()

        # Step 1: Manager needs to approve
        step2_1 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow2.id,
            step_no=1,
            assignee_id=manager_id,
            status="PENDING",
            action=None,
            comment=None,
            completed_at=None,
        )
        db.add(step2_1)

        # Step 2: Director needs to approve
        step2_2 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow2.id,
            step_no=2,
            assignee_id=director_id,
            status="PENDING",
            action=None,
            comment=None,
            completed_at=None,
        )
        db.add(step2_2)

        # Mock Payment 3: APPROVED (manager approved, waiting for director)
        payment3 = PaymentBoard(
            id=str(uuid.uuid4()),
            code="PAY-DEMO-003",
            customer_id="CUS002",
            contract_id="CTR-SEED-003",
            price_table_id="PL-2026-003",
            period_start="2026-07-01",
            period_end="2026-07-31",
            sub_total=Decimal("18812500.00"),
            tax_percent=Decimal("10.00"),
            tax_amount=Decimal("1881250.00"),
            total_amount=Decimal("20693750.00"),
            status="SUBMITTED",
            created_by=staff_id,
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        db.add(payment3)
        db.flush()

        detail3 = PaymentDetail(
            id=str(uuid.uuid4()),
            payment_board_id=payment3.id,
            service_code="SRV-PORT-OP",
            service_name="Khai thác bến bãi hạ tải",
            unit="Tấn",
            quantity=Decimal("150.50"),
            unit_price=Decimal("125000.00"),
            total_price=Decimal("18812500.00"),
        )
        db.add(detail3)

        # Workflow for payment3 - manager already approved
        workflow3 = PaymentWorkflow(
            id=str(uuid.uuid4()),
            payment_board_id=payment3.id,
            current_step=2,
            status="IN_PROGRESS",
        )
        db.add(workflow3)
        db.flush()

        # Step 1: Manager already approved
        step3_1 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow3.id,
            step_no=1,
            assignee_id=manager_id,
            status="COMPLETED",
            action="APPROVED",
            comment="Kiểm tra tài liệu xong, đủ điều kiện duyệt.",
            completed_at=datetime.utcnow() - timedelta(hours=4),
        )
        db.add(step3_1)

        # Step 2: Director waiting to approve
        step3_2 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow3.id,
            step_no=2,
            assignee_id=director_id,
            status="PENDING",
            action=None,
            comment=None,
            completed_at=None,
        )
        db.add(step3_2)

        # Mock Payment 4: REJECTED (director từ chối)
        payment4 = PaymentBoard(
            id=str(uuid.uuid4()),
            code="PAY-DEMO-004",
            customer_id="CUS002",
            contract_id="CTR-SEED-004",
            price_table_id="PL-2026-003",
            period_start="2026-08-01",
            period_end="2026-08-31",
            sub_total=Decimal("56654400.00"),
            tax_percent=Decimal("10.00"),
            tax_amount=Decimal("5665440.00"),
            total_amount=Decimal("62319840.00"),
            status="REJECTED",
            created_by=staff_id,
            created_at=datetime.utcnow() - timedelta(days=2),
        )
        db.add(payment4)
        db.flush()

        detail4 = PaymentDetail(
            id=str(uuid.uuid4()),
            payment_board_id=payment4.id,
            service_code="SRV-40ft-OUT",
            service_name="Bốc xếp container 40ft (Hàng xuất)",
            unit="Khối",
            quantity=Decimal("88.80"),
            unit_price=Decimal("638000.00"),
            total_price=Decimal("56654400.00"),
        )
        db.add(detail4)

        # Workflow for payment4 - rejected at step 2
        workflow4 = PaymentWorkflow(
            id=str(uuid.uuid4()),
            payment_board_id=payment4.id,
            current_step=2,
            status="COMPLETED",
        )
        db.add(workflow4)
        db.flush()

        # Step 1: Manager approved
        step4_1 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow4.id,
            step_no=1,
            assignee_id=manager_id,
            status="COMPLETED",
            action="APPROVED",
            comment="OK, chuyển cho giám đốc.",
            completed_at=datetime.utcnow() - timedelta(hours=20),
        )
        db.add(step4_1)

        # Step 2: Director rejected
        step4_2 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow4.id,
            step_no=2,
            assignee_id=director_id,
            status="REJECTED",
            action="REJECTED",
            comment="Đơn giá quá cao so với bảng giá niêm yết. Yêu cầu thương lượng lại với khách hàng.",
            completed_at=datetime.utcnow() - timedelta(hours=2),
        )
        db.add(step4_2)

        # Mock Payment 5: REVISION_REQUESTED (yêu cầu sửa)
        payment5 = PaymentBoard(
            id=str(uuid.uuid4()),
            code="PAY-DEMO-005",
            customer_id="CUS001",
            contract_id="CTR-SEED-005",
            price_table_id="PL-2026-003",
            period_start="2026-08-01",
            period_end="2026-08-31",
            sub_total=Decimal("24000000.00"),
            tax_percent=Decimal("10.00"),
            tax_amount=Decimal("2400000.00"),
            total_amount=Decimal("26400000.00"),
            status="REVISION_REQUESTED",
            created_by=staff_id,
            created_at=datetime.utcnow() - timedelta(days=3),
        )
        db.add(payment5)
        db.flush()

        detail5 = PaymentDetail(
            id=str(uuid.uuid4()),
            payment_board_id=payment5.id,
            service_code="SRV-CUST-CLR",
            service_name="Khai báo hải quan trọn gói",
            unit="Tờ khai",
            quantity=Decimal("30.00"),
            unit_price=Decimal("800000.00"),
            total_price=Decimal("24000000.00"),
        )
        db.add(detail5)

        # Workflow for payment5 - revision requested at step 1
        workflow5 = PaymentWorkflow(
            id=str(uuid.uuid4()),
            payment_board_id=payment5.id,
            current_step=1,
            status="COMPLETED",
        )
        db.add(workflow5)
        db.flush()

        # Step 1: Manager requested revision
        step5_1 = PaymentWorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow5.id,
            step_no=1,
            assignee_id=manager_id,
            status="COMPLETED",
            action="REVISION_REQUESTED",
            comment="Cần cập nhật thông tin khách hàng và sản lượng lại. Thời kỳ tính phí chưa chính xác.",
            completed_at=datetime.utcnow() - timedelta(hours=8),
        )
        db.add(step5_1)

        db.commit()
        print("✅ Tạo thành công 5 mock payments với workflows!")
        print(f"  - PAY-DEMO-001: CALCULATED (draft, chờ đối soát)")
        print(f"  - PAY-DEMO-002: SUBMITTED (chờ manager duyệt)")
        print(f"  - PAY-DEMO-003: SUBMITTED (manager duyệt rồi, chờ director)")
        print(f"  - PAY-DEMO-004: REJECTED (director từ chối)")
        print(f"  - PAY-DEMO-005: REVISION_REQUESTED (yêu cầu sửa)")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi seed dữ liệu: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_payments()
