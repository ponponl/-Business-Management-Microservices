# ĐATH Quản trị kinh doanh

Business Management Microservices project - handling customers, contracts, pricing, production volumes, and payment workflows with approval and e-signature integration.

## Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)
- Node.js 18+ (for UI)
- PostgreSQL (runs in Docker)
- Kafka & Zookeeper (runs in Docker)

## Chạy toàn bộ project bằng Docker

Thực hiện các lệnh sau từ thư mục gốc của project:

### 1. Khởi động backend và hạ tầng

```powershell
docker compose up -d --build
docker compose ps
```

Compose khởi động 16 container gồm API Gateway, 5 backend services, esign worker, 5 PostgreSQL, Redis, Kafka, Zookeeper và Kafka UI.

Lưu ý: `notification_service` hiện chưa được khai báo trong `docker-compose.yml`, nên không được khởi động bởi lệnh trên.

Đợi Kafka chuyển sang trạng thái `healthy` và các database sẵn sàng trước khi seed:

```powershell
docker inspect --format='{{.State.Health.Status}}' kafka
docker exec postgres-auth pg_isready -U admin -d db_auth
docker exec postgres-pricing pg_isready -U admin -d db_pricing
docker exec postgres-contract pg_isready -U admin -d db_contract
docker exec postgres-production pg_isready -U admin -d db_production
docker exec postgres-payment pg_isready -U admin -d db_payment
```

Nếu chưa sẵn sàng, chờ vài giây rồi chạy lại các lệnh kiểm tra trên. Có thể xem log bằng:

```powershell
docker compose logs -f auth-service pricing-service contract-service production-service payment-service
```

### 2. Migration và seed dữ liệu

Chạy đúng thứ tự sau. `seed_customer.py` phải chạy trước `seed_contract.py` vì contract seed tham chiếu đến customer.

```powershell
# Tạo/cập nhật schema Contract Service
docker compose exec contract-service alembic upgrade head

# Tạo tài khoản mẫu
docker compose exec auth-service python seed.py

# Tạo customers và contracts mẫu
docker compose exec contract-service python seed_customer.py
docker compose exec contract-service python seed_contract.py

# Tạo bảng giá mẫu
docker compose exec pricing-service python -m app.seed

# Tạo sản lượng mẫu
docker compose exec production-service python seed_production.py

# Tạo payment và workflow mẫu
docker compose exec payment-service python seed.py
```

Các seed của pricing, production và payment có thể xóa rồi tạo lại dữ liệu của service tương ứng. Không chạy các script này trên dữ liệu cần giữ lại.

### 3. Khởi động giao diện React

Mở terminal thứ hai:

```powershell
cd ui
npm install
npm run dev
```

Mở trình duyệt tại [http://localhost:5173](http://localhost:5173). UI gọi API thông qua Gateway tại `http://localhost:8080`.

Các địa chỉ quan trọng:

- API Gateway: `http://localhost:8080`
- Kafka UI: `http://localhost:8086`
- Auth Service: `http://localhost:8081`
- Pricing Service: `http://localhost:8082`
- Contract Service: `http://localhost:8083`
- Production Service: `http://localhost:8084`
- Payment Service: `http://localhost:8085`

### 4. Tài khoản mẫu và kiểm thử payment workflow

Các tài khoản được tạo bởi `services/auth_service/seed.py` đều dùng mật khẩu `Password@123`:

- Staff: `staff01`
- Manager: `manager01`
- Director: `director01`

Quy trình payment:

1. Đăng nhập bằng `staff01`, tạo payment mới và gửi duyệt.
2. Đăng xuất, đăng nhập bằng `manager01` và duyệt payment.
3. Đăng xuất, đăng nhập bằng `director01` và duyệt payment.
4. Gửi ký, nhận kết quả ký, sau đó phát hành payment.

## Project Structure

```
├── docker-compose.yml          # Service orchestration
├── gateway/
│   └── nginx.conf             # API Gateway routing
├── services/
│   ├── auth_service/          # JWT & user management
│   ├── contract_service/      # Contract CRUD & validation
│   ├── pricing_service/       # Price table management
│   ├── production_service/    # Volume tracking
│   └── payment_service/       # Payment workflow (core)
│       ├── models/            # Database schemas
│       ├── schemas/           # Pydantic models
│       ├── services/          # Business logic
│       ├── utils/             # Helpers
│       └── main.py            # FastAPI app
└── ui/                         # React + Vite frontend
    └── src/
        ├── pages/             # UI screens
        ├── components/        # Reusable components
        └── App.jsx            # Main app
```

## Services Overview

### Payment Service (Core)
- **Endpoints**: 18 routes covering full lifecycle
  - POST `/api/payments` - Create payment
  - POST `/api/payments/{id}/reconcile` - Reconcile
  - POST `/api/payments/{id}/submit` - Submit for approval
  - POST `/api/payments/{id}/approve` - Manager/Director approval
  - POST `/api/payments/{id}/reject` - Reject
  - POST `/api/payments/{id}/request-revision` - Request changes
  - POST `/api/payments/{id}/send-sign` - Send to e-signature
  - GET `/api/payments/{id}/signatures` - Get e-signature audit history
  - POST `/api/payments/{id}/issue` - Issue (finalize)
  - GET `/api/payments` - List payments
  - GET `/api/payments/{id}` - Get payment details
  - GET `/api/payments/{id}/workflow` - Get approval workflow
  - GET `/api/payments/stats` - Payment statistics
  - POST `/api/payments/{id}/adjustment` - Create amendment

The e-signature flow is handled asynchronously by `services/payment_service/esign_worker.py` via the `payment.signing` Kafka topic and the Payment Service database.
  - POST `/api/payments/{id}/cancel-sign` - Cancel signing
  - POST `/api/payments/outbox/pending` - Check outbox queue

- **Validations**:
  - Contract Service: contract status & effective period
  - Pricing Service: price table validity & unit prices
  - Production Service: volume locked/reconciled status

- **Workflow Features**:
  - Multi-step approval (manager → director)
  - Per-step assignee checking
  - Idempotency-Key for duplicate prevention
  - Outbox pattern + Kafka for reliable event publishing

- **Status Lifecycle**:
  ```
  CALCULATED → RECONCILED → SUBMITTED → APPROVED → SIGNING → SIGNED → ISSUED
  ```

### Other Services

- **Auth Service**: JWT token generation, user roles (STAFF/MANAGER/DIRECTOR)
- **Contract Service**: Contract management, effective period tracking
- **Pricing Service**: Price tables with effective dates, unit price snapshots
- **Production Service**: Production volumes, period locking mechanism

## Environment Setup

### Local Development (without Docker)

```bash
# Install Payment Service dependencies
cd services/payment_service
pip install -r requirements.txt

# Run migrations (if needed)
# DATABASE_URL="postgresql://user:pass@localhost/db_payment" python -m alembic upgrade head

# Start service
DATABASE_URL="postgresql://admin:password123@localhost:5435/db_payment" \
KAFKA_BOOTSTRAP_SERVERS="localhost:29092" \
python main.py
```

### Database URLs

- Auth: `postgresql://admin:password123@localhost:5431/db_auth`
- Pricing: `postgresql://admin:password123@localhost:5432/db_pricing`
- Contract: `postgresql://admin:password123@localhost:5433/db_contract`
- Production: `postgresql://admin:password123@localhost:5434/db_production`
- Payment: `postgresql://admin:password123@localhost:5435/db_payment`

## API Gateway

All requests go through **Nginx** at `http://localhost:8080`:

```
GET/POST /api/v1/auth/* → Auth Service (8081)
GET/POST /api/v1/price-lists/* → Pricing Service (8082)
GET/POST /api/v1/approvals/* → Pricing Service (8082)
GET/POST /api/v1/contracts/* → Contract Service (8083)
GET/POST /api/v1/customers/* → Contract Service (8083)
GET/POST /api/v1/volumes/* → Production Service (8084)
GET/POST /api/v1/payments/* → Payment Service (8085)
```

Requests include headers:
- `Authorization: Bearer <JWT_TOKEN>`
- `X-User: <user_id>`
- `X-Approval-Assignees: <comma,separated,ids>` (for workflow setup)
- `Idempotency-Key: <uuid>` (for payment creation)

## Testing

### Test Payment Creation with Validation
```bash
# Mock request (adjust IDs to your test data)
curl -X POST http://localhost:8080/api/v1/payments \
  -H "Authorization: Bearer <token>" \
  -H "X-User: staff01" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust-123",
    "contract_id": "ctr-456",
    "price_table_id": "price-789",
    "period_start": "2026-09-01",
    "period_end": "2026-09-30",
    "tax_percent": 10,
    "items": [
      {
        "service_code": "SHIPPING",
        "service_name": "Shipping Service",
        "unit": "container",
        "quantity": 5,
        "unit_price": 100
      }
    ]
  }'
```

### Test Workflow Approval
```bash
# Manager approves
curl -X POST http://localhost:8080/api/v1/payments/{payment_id}/approve \
  -H "Authorization: Bearer <manager_token>" \
  -H "X-User: manager01" \
  -H "Content-Type: application/json" \
  -d '{"comment": "Approved - ready for director review"}'
```

## Troubleshooting

### Services won't start
```powershell
# Check Docker logs
docker compose logs payment-service
docker compose logs auth-service

# Restart all services
docker compose down
docker compose up -d --build
```

### Database connection failed
```powershell
# Verify DB containers are running
docker compose ps

# Re-initialize database (lose data!)
docker compose down -v
docker compose up -d --build
```

### Kafka connection issues
```powershell
# Check Kafka is running
docker compose ps kafka

# View Kafka topics
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

### Payment validation fails
- Ensure Contract Service has the contract with active status
- Ensure Pricing Service has effective price tables
- Ensure Production Service has locked volumes for the period
- Check service logs: `docker logs <service-name>`

## Key Design Decisions

1. **Contract Validation First**: Payment creation checks contract status before pricing/volumes
2. **Outbox Pattern**: Events stored in DB then published to Kafka → reliable event delivery
3. **Idempotency Key**: Prevents duplicate payment creation on retry
4. **Row-level Locking**: Payment workflow steps use FOR UPDATE to prevent race conditions
5. **Snapshot Pricing**: Unit price captured at creation time, unaffected by later price changes
6. **Multi-step Workflow**: Each payment requires approval by multiple roles (manager, director)

## Performance Notes

- Payment creation (~200ms): Contract → Pricing → Production validation
- Workflow approval (immediate): In-database step update + Kafka event publish
- Outbox publisher: Polls every 2 seconds, publishes events with retry logic
- Database: Separate schema per service (no shared DB)

## Support

For issues or questions about the workflow, check:
- Service logs: `docker logs <service-name>`
- Database state: Connect to PostgreSQL and query payment_boards, payment_workflow_instances
- Kafka events: Kafka UI at http://localhost:8086

## Credentials

**Test Users** (from auth-service seed):
- staff01 / Password@123
- manager01 / Password@123
- director01 / Password@123

**Database** (all services):
- User: admin
- Password: password123

---

**Tech Stack**: FastAPI, PostgreSQL, Kafka, React, Docker, Nginx