import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.db.session import SessionLocal

from app.models.customer import Customer
from app.models.contract import Contract
from app.models.contract_version import ContractVersion
from app.models.contract_approval import ContractApproval
from app.models.contract_audit import ContractAudit
from app.models.outbox_event import OutboxEvent


# ============================================================
# SEED ACTOR IDS
# ============================================================
# Đây là logical reference tới Auth Service.
#
# Contract Service KHÔNG có FK trực tiếp tới auth.users.
# Hiện tại Auth Service của nhóm bạn đang generate UUID động,
# nên các UUID này chỉ dùng làm actor/approver reference cho
# dữ liệu seed.
#
# Sau này nếu nhóm thống nhất UUID cố định cho Auth seed,
# có thể thay các UUID này bằng UUID tương ứng.
# ============================================================

SEED_STAFF_ID = UUID(
    "00000000-0000-0000-0000-000000000001"
)

SEED_MANAGER_ID = UUID(
    "00000000-0000-0000-0000-000000000002"
)


# ============================================================
# NAMESPACE CHO SEED EVENT ID
# ============================================================
# Dùng uuid5 để cùng một Contract + Event Type luôn tạo ra
# cùng một event_id.
#
# Ví dụ:
# CTR-SEED-001 + CONTRACT_ACTIVATED
# -> luôn ra cùng event_id
#
# Nhờ đó chạy seed nhiều lần không tạo duplicate event.
# ============================================================

SEED_EVENT_NAMESPACE = UUID(
    "20000000-0000-0000-0000-000000000001"
)


# ============================================================
# SEED CONTRACT DATA
# ============================================================
#
# Chỉ seed các Contract ACTIVE.
#
# CUS001 và CUS002 đều ACTIVE.
# CUS003 đang INACTIVE nên không sử dụng.
#
# Một số Contract có version 2 để phục vụ test versioning.
#
# Tại thời điểm seed hiện tại:
#   2026-09-01
#
# effective_to = 2026-12-31
# -> Contract vẫn đang ACTIVE và còn hiệu lực.
# ============================================================

CONTRACTS = [
    {
        "contract_id": UUID(
            "10000000-0000-0000-0000-000000000001"
        ),
        "contract_number": "CTR-SEED-001",
        "customer_code": "CUS001",
        "current_version": 1,
        "status": "ACTIVE",
        "versions": [
            {
                "version_no": 1,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("100000000.00"),
                "payment_terms": (
                    "Thanh toán trong vòng 30 ngày "
                    "kể từ ngày nhận đầy đủ chứng từ."
                ),
                "service_terms": (
                    "Dịch vụ logistics tiêu chuẩn."
                ),
                "change_reason": "Initial contract version",
            }
        ],
    },
    {
        "contract_id": UUID(
            "10000000-0000-0000-0000-000000000002"
        ),
        "contract_number": "CTR-SEED-002",
        "customer_code": "CUS001",
        "current_version": 2,
        "status": "ACTIVE",
        "versions": [
            {
                "version_no": 1,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("120000000.00"),
                "payment_terms": (
                    "Thanh toán trong vòng 30 ngày."
                ),
                "service_terms": (
                    "Dịch vụ vận chuyển và kho bãi."
                ),
                "change_reason": "Initial contract version",
            },
            {
                "version_no": 2,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("150000000.00"),
                "payment_terms": (
                    "Thanh toán trong vòng 30 ngày."
                ),
                "service_terms": (
                    "Bổ sung dịch vụ kho bãi và vận chuyển "
                    "nội địa."
                ),
                "change_reason": "Updated service scope",
            },
        ],
    },
    {
        "contract_id": UUID(
            "10000000-0000-0000-0000-000000000003"
        ),
        "contract_number": "CTR-SEED-003",
        "customer_code": "CUS002",
        "current_version": 1,
        "status": "ACTIVE",
        "versions": [
            {
                "version_no": 1,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("200000000.00"),
                "payment_terms": (
                    "Thanh toán hàng tháng."
                ),
                "service_terms": (
                    "Dịch vụ vận chuyển container."
                ),
                "change_reason": "Initial contract version",
            }
        ],
    },
    {
        "contract_id": UUID(
            "10000000-0000-0000-0000-000000000004"
        ),
        "contract_number": "CTR-SEED-004",
        "customer_code": "CUS002",
        "current_version": 2,
        "status": "ACTIVE",
        "versions": [
            {
                "version_no": 1,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("180000000.00"),
                "payment_terms": (
                    "Thanh toán trong vòng 45 ngày."
                ),
                "service_terms": (
                    "Dịch vụ logistics và hàng rời."
                ),
                "change_reason": "Initial contract version",
            },
            {
                "version_no": 2,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("220000000.00"),
                "payment_terms": (
                    "Thanh toán trong vòng 30 ngày."
                ),
                "service_terms": (
                    "Mở rộng phạm vi dịch vụ logistics."
                ),
                "change_reason": "Expanded service scope",
            },
        ],
    },
    {
        "contract_id": UUID(
            "10000000-0000-0000-0000-000000000005"
        ),
        "contract_number": "CTR-SEED-005",
        "customer_code": "CUS001",
        "current_version": 2,
        "status": "ACTIVE",
        "versions": [
            {
                "version_no": 1,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("250000000.00"),
                "payment_terms": (
                    "Thanh toán hàng tháng."
                ),
                "service_terms": (
                    "Dịch vụ logistics tổng hợp."
                ),
                "change_reason": "Initial contract version",
            },
            {
                "version_no": 2,
                "effective_from": date(2026, 1, 1),
                "effective_to": date(2026, 12, 31),
                "contract_value": Decimal("300000000.00"),
                "payment_terms": (
                    "Thanh toán hàng tháng."
                ),
                "service_terms": (
                    "Dịch vụ logistics mở rộng "
                    "và quản lý kho."
                ),
                "change_reason": "Updated contract terms",
            },
        ],
    },
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_customer(
    db,
    customer_code: str,
) -> Customer:
    """
    Tìm Customer theo customer_code.

    Contract seed KHÔNG tự tạo Customer.
    Phải chạy seed_customer.py trước.
    """

    customer = (
        db.query(Customer)
        .filter(
            Customer.customer_code == customer_code
        )
        .first()
    )

    if customer is None:
        raise RuntimeError(
            f"Customer '{customer_code}' không tồn tại. "
            "Hãy chạy seed_customer.py trước."
        )

    if customer.status != "ACTIVE":
        raise RuntimeError(
            f"Customer '{customer_code}' không ACTIVE."
        )

    return customer


def get_seed_event_id(
    contract_id: UUID,
    event_type: str,
) -> UUID:
    """
    Tạo event_id deterministic cho seed event.
    """

    return uuid.uuid5(
        SEED_EVENT_NAMESPACE,
        f"{contract_id}:{event_type}",
    )


def create_or_get_contract(
    db,
    data: dict,
):
    """
    Tạo Contract nếu chưa tồn tại.
    """

    contract = (
        db.query(Contract)
        .filter(
            Contract.contract_number
            == data["contract_number"]
        )
        .first()
    )

    if contract is not None:
        return contract, False

    customer = get_customer(
        db,
        data["customer_code"],
    )

    contract = Contract(
        contract_id=data["contract_id"],
        contract_number=data["contract_number"],
        customer_id=customer.customer_id,
        current_version=data["current_version"],
        status=data["status"],
        row_version=1,
    )

    db.add(contract)
    db.flush()

    return contract, True


def create_or_get_versions(
    db,
    contract: Contract,
    data: dict,
):
    """
    Tạo các Contract Version.
    """

    versions = []

    for version_data in data["versions"]:

        version = (
            db.query(ContractVersion)
            .filter(
                ContractVersion.contract_id
                == contract.contract_id,

                ContractVersion.version_no
                == version_data["version_no"],
            )
            .first()
        )

        if version is None:

            version = ContractVersion(
                contract_id=contract.contract_id,
                version_no=(
                    version_data["version_no"]
                ),
                effective_from=(
                    version_data["effective_from"]
                ),
                effective_to=(
                    version_data["effective_to"]
                ),
                contract_value=(
                    version_data["contract_value"]
                ),
                payment_terms=(
                    version_data["payment_terms"]
                ),
                service_terms=(
                    version_data["service_terms"]
                ),
                created_by=SEED_STAFF_ID,
                change_reason=(
                    version_data["change_reason"]
                ),
            )

            db.add(version)
            db.flush()

        versions.append(version)

    return versions


def get_current_version(
    contract: Contract,
    versions: list[ContractVersion],
):
    """
    Lấy Version hiện hành theo contracts.current_version.
    """

    for version in versions:

        if (
            version.version_no
            == contract.current_version
        ):
            return version

    raise RuntimeError(
        f"Không tìm thấy current version "
        f"{contract.current_version} "
        f"cho contract "
        f"{contract.contract_number}."
    )


def create_or_get_approval(
    db,
    contract: Contract,
):
    """
    Seed một approval record đã APPROVED.

    Vì Contract seed cuối cùng là ACTIVE,
    approval phải thể hiện rằng Contract đã được phê duyệt.
    """

    approval = (
        db.query(ContractApproval)
        .filter(
            ContractApproval.contract_id
            == contract.contract_id,

            ContractApproval.step_no == 1,
        )
        .first()
    )

    if approval is not None:
        return approval

    approval = ContractApproval(
        contract_id=contract.contract_id,
        step_no=1,
        approver_id=SEED_MANAGER_ID,
        status="APPROVED",
        comment=(
            "Seed data: Hợp đồng đã được phê duyệt."
        ),
    )

    db.add(approval)
    db.flush()

    return approval


def audit_exists(
    db,
    contract_id: UUID,
    action: str,
    version_id: UUID | None,
):
    """
    Kiểm tra audit seed đã tồn tại hay chưa.
    """

    query = (
        db.query(ContractAudit)
        .filter(
            ContractAudit.contract_id
            == contract_id,

            ContractAudit.action
            == action,
        )
    )

    if version_id is None:
        query = query.filter(
            ContractAudit.version_id.is_(None)
        )
    else:
        query = query.filter(
            ContractAudit.version_id
            == version_id
        )

    return query.first()


def create_audits(
    db,
    contract: Contract,
    versions: list[ContractVersion],
):
    """
    Tạo audit history mô phỏng lifecycle:

        CREATE
        UPDATE (nếu có V2)
        SUBMIT
        START_REVIEW
        APPROVE
        ACTIVATE

    Đây chỉ là dữ liệu bootstrap/history cho demo.
    Business transition thật vẫn phải đi qua API.
    """

    current_version = get_current_version(
        contract,
        versions,
    )

    ordered_versions = sorted(
        versions,
        key=lambda item: item.version_no,
    )

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    if audit_exists(
        db,
        contract.contract_id,
        "CREATE",
        ordered_versions[0].version_id,
    ) is None:

        db.add(
            ContractAudit(
                contract_id=contract.contract_id,
                version_id=(
                    ordered_versions[0].version_id
                ),
                actor_id=SEED_STAFF_ID,
                action="CREATE",
                status_before=None,
                status_after="DRAFT",
                note="Seed data: tạo hợp đồng.",
            )
        )

    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    if len(ordered_versions) > 1:

        for index in range(
            1,
            len(ordered_versions),
        ):

            previous_version = (
                ordered_versions[index - 1]
            )

            new_version = (
                ordered_versions[index]
            )

            if audit_exists(
                db,
                contract.contract_id,
                "UPDATE",
                new_version.version_id,
            ) is None:

                db.add(
                    ContractAudit(
                        contract_id=(
                            contract.contract_id
                        ),
                        version_id=(
                            new_version.version_id
                        ),
                        actor_id=SEED_STAFF_ID,
                        action="UPDATE",
                        status_before="DRAFT",
                        status_after="DRAFT",
                        note=(
                            "Seed data: cập nhật từ "
                            f"version "
                            f"{previous_version.version_no} "
                            "sang version "
                            f"{new_version.version_no}."
                        ),
                    )
                )

    # --------------------------------------------------------
    # SUBMIT
    # --------------------------------------------------------

    if audit_exists(
        db,
        contract.contract_id,
        "SUBMIT",
        current_version.version_id,
    ) is None:

        db.add(
            ContractAudit(
                contract_id=contract.contract_id,
                version_id=current_version.version_id,
                actor_id=SEED_STAFF_ID,
                action="SUBMIT",
                status_before="DRAFT",
                status_after="SUBMITTED",
                note=(
                    "Seed data: gửi hợp đồng "
                    "để phê duyệt."
                ),
            )
        )

    # --------------------------------------------------------
    # START_REVIEW
    # --------------------------------------------------------

    if audit_exists(
        db,
        contract.contract_id,
        "START_REVIEW",
        current_version.version_id,
    ) is None:

        db.add(
            ContractAudit(
                contract_id=contract.contract_id,
                version_id=current_version.version_id,
                actor_id=SEED_MANAGER_ID,
                action="START_REVIEW",
                status_before="SUBMITTED",
                status_after="UNDER_REVIEW",
                note=(
                    "Seed data: bắt đầu "
                    "quy trình phê duyệt."
                ),
            )
        )

    # --------------------------------------------------------
    # APPROVE
    # --------------------------------------------------------

    if audit_exists(
        db,
        contract.contract_id,
        "APPROVE",
        current_version.version_id,
    ) is None:

        db.add(
            ContractAudit(
                contract_id=contract.contract_id,
                version_id=current_version.version_id,
                actor_id=SEED_MANAGER_ID,
                action="APPROVE",
                status_before="UNDER_REVIEW",
                status_after="APPROVED",
                note=(
                    "Seed data: hợp đồng "
                    "được phê duyệt."
                ),
            )
        )

    # --------------------------------------------------------
    # ACTIVATE
    # --------------------------------------------------------

    if audit_exists(
        db,
        contract.contract_id,
        "ACTIVATE",
        current_version.version_id,
    ) is None:

        db.add(
            ContractAudit(
                contract_id=contract.contract_id,
                version_id=current_version.version_id,
                actor_id=SEED_MANAGER_ID,
                action="ACTIVATE",
                status_before="APPROVED",
                status_after="ACTIVE",
                note=(
                    "Seed data: hợp đồng "
                    "được kích hoạt."
                ),
            )
        )

    db.flush()


def create_or_get_activation_outbox(
    db,
    contract: Contract,
    current_version: ContractVersion,
):
    """
    Tạo bootstrap event CONTRACT_ACTIVATED cho Volume/Pricing/Payment.

    Đây không phải là business transition đang diễn ra thực tế.
    Nó là event bootstrap giúp downstream service nhận biết
    Contract seed hiện đang ACTIVE và khởi tạo local cache/reference.

    Outbox Publisher sẽ publish event này sang:
        contract.events
    """

    event_type = "CONTRACT_ACTIVATED"

    event_id = get_seed_event_id(
        contract.contract_id,
        event_type,
    )

    existing = (
        db.query(OutboxEvent)
        .filter(
            OutboxEvent.event_id == event_id
        )
        .first()
    )

    if existing is not None:
        return existing

    occurred_at = datetime.now(
        timezone.utc
    )

    # --------------------------------------------------------
    # Event envelope phải khớp với event contract
    # hiện tại của Contract Service.
    #
    # QUAN TRỌNG:
    # UUID/date phải convert sang string,
    # vì JSONB cần JSON-serializable values.
    # --------------------------------------------------------

    payload = {
        "event_id": str(event_id),

        "event_name": event_type,

        "occurred_at": (
            occurred_at.isoformat()
        ),

        "aggregate_type": "CONTRACT",

        "aggregate_id": str(
            contract.contract_id
        ),

        # Version của EVENT SCHEMA,
        # không phải Contract Version.
        "version": 1,

        "payload": {
            "contract_id": str(
                contract.contract_id
            ),

            "contract_number": (
                contract.contract_number
            ),

            "customer_id": str(
                contract.customer_id
            ),

            "current_version": (
                contract.current_version
            ),

            "status": contract.status,

            "effective_from": (
                current_version
                .effective_from
                .isoformat()
            ),

            "effective_to": (
                current_version
                .effective_to
                .isoformat()
            ),
        },
    }

    outbox_event = OutboxEvent(
        event_id=event_id,
        aggregate_type="CONTRACT",
        aggregate_id=contract.contract_id,
        event_type=event_type,
        payload=payload,
        status="PENDING",
        retry_count=0,
        occurred_at=occurred_at,
    )

    db.add(outbox_event)
    db.flush()

    return outbox_event


# ============================================================
# MAIN SEED
# ============================================================

def seed_contracts():
    db = SessionLocal()

    created_count = 0
    skipped_count = 0
    outbox_created_count = 0

    try:

        print("=" * 70)
        print("🌱 CONTRACT SERVICE - SEED DATA")
        print("=" * 70)

        for contract_data in CONTRACTS:

            # ------------------------------------------------
            # 1. CONTRACT
            # ------------------------------------------------

            contract, created = (
                create_or_get_contract(
                    db,
                    contract_data,
                )
            )

            if created:
                created_count += 1

                print(
                    f"  + Contract "
                    f"{contract.contract_number} "
                    f"[{contract.status}] "
                    f"customer="
                    f"{contract_data['customer_code']} "
                    f"version="
                    f"{contract.current_version}"
                )

            else:
                skipped_count += 1

                print(
                    f"  - Contract "
                    f"{contract.contract_number} "
                    "đã tồn tại."
                )

            # ------------------------------------------------
            # 2. VERSIONS
            # ------------------------------------------------

            versions = create_or_get_versions(
                db,
                contract,
                contract_data,
            )

            print(
                f"      Versions: "
                f"{len(versions)}"
            )

            # ------------------------------------------------
            # 3. APPROVAL
            # ------------------------------------------------

            create_or_get_approval(
                db,
                contract,
            )

            print(
                "      Approval: APPROVED"
            )

            # ------------------------------------------------
            # 4. AUDITS
            # ------------------------------------------------

            create_audits(
                db,
                contract,
                versions,
            )

            print(
                "      Audit: lifecycle history created"
            )

            # ------------------------------------------------
            # 5. OUTBOX
            # ------------------------------------------------

            current_version = get_current_version(
                contract,
                versions,
            )

            existing_event = (
                db.query(OutboxEvent)
                .filter(
                    OutboxEvent.event_id
                    == get_seed_event_id(
                        contract.contract_id,
                        "CONTRACT_ACTIVATED",
                    )
                )
                .first()
            )

            if existing_event is None:

                create_or_get_activation_outbox(
                    db,
                    contract,
                    current_version,
                )

                outbox_created_count += 1

                print(
                    "      Outbox: "
                    "CONTRACT_ACTIVATED [PENDING]"
                )

            else:

                print(
                    "      Outbox: "
                    "CONTRACT_ACTIVATED đã tồn tại"
                )

        # ----------------------------------------------------
        # COMMIT ALL DATA
        # ----------------------------------------------------

        db.commit()

        print("=" * 70)
        print("✅ SEED CONTRACT HOÀN TẤT")
        print("=" * 70)
        print(
            f"   Contract created : {created_count}"
        )
        print(
            f"   Contract skipped : {skipped_count}"
        )
        print(
            f"   Outbox created   : "
            f"{outbox_created_count}"
        )
        print("=" * 70)

    except Exception as exc:

        db.rollback()

        print("=" * 70)
        print("❌ SEED CONTRACT THẤT BẠI")
        print("=" * 70)
        print(f"   Error: {exc}")
        print("=" * 70)

        raise

    finally:

        db.close()


if __name__ == "__main__":
    seed_contracts()