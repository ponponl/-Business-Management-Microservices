# Payment Service - Luồng quản lý bảng thanh toán

## 1. Phạm vi

Payment Service chịu trách nhiệm lập và quản lý vòng đời bảng thanh toán dựa trên:

- `customer_id`: ID khách hàng do service sở hữu khách hàng cung cấp.
- `contract_id`: ID hợp đồng do Contract Service cung cấp.
- `price_table_id`: ID hoặc mã bảng giá do Pricing Service cung cấp.
- Sản lượng thực tế do Production Service cung cấp.

Payment không sở hữu dữ liệu khách hàng, hợp đồng hoặc bảng giá. Payment chỉ lưu các ID tham chiếu và snapshot dữ liệu cần thiết để lập bảng thanh toán.

> Lưu ý: Contract Service hiện tại trong repository chỉ có health endpoint `/`, chưa có API nghiệp vụ để Payment xác thực hợp đồng. Vì vậy luồng Contract bên dưới là luồng tích hợp cần bổ sung sau khi Contract Service cung cấp API.

## 2. Kiến trúc tổng quan

```mermaid
flowchart LR
    UI[Payment UI]
    GW[API Gateway]
    PAY[Payment Service]
    DB[(PostgreSQL payment)]
    CONTRACT[Contract Service]
    PRICE[Pricing Service]
    PROD[Production Service]
    KAFKA[(Kafka)]
    NOTIFY[Notification / Consumer Services]

    UI -->|HTTP + JWT| PAY
    UI -->|qua gateway nếu cấu hình| GW
    GW --> PAY
    PAY --> DB
    PAY -->|POST validate-for-payment| PRICE
    PAY -->|GET volumes + period_key| PROD
    PAY -.->|cần bổ sung API validation| CONTRACT
    PAY -->|Outbox worker| KAFKA
    KAFKA --> NOTIFY
```

Payment Service chạy trực tiếp ở `http://localhost:8085` trong môi trường Docker Compose.

Các biến môi trường tích hợp:

```text
DATABASE_URL=postgresql://admin:password123@postgres-payment:5432/db_payment
PRICING_SERVICE_URL=http://pricing-service:8000
PRODUCTION_SERVICE_URL=http://production-service:8000
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
```

## 3. Database của Payment

### 3.1. Bảng nghiệp vụ chính

#### `payment_boards`

Lưu thông tin tổng quát của bảng thanh toán:

```text
id
code
customer_id
contract_id
price_table_id
period_start
period_end
sub_total
tax_percent
tax_amount
total_amount
status
reference_id
created_by
created_at
updated_at
```

Payment chỉ lưu `customer_id`, `contract_id`, `price_table_id`, không lưu tên khách hàng hoặc thông tin chi tiết hợp đồng.

#### `payment_details`

Lưu các dòng dịch vụ và snapshot tại thời điểm tính phí:

```text
id
payment_board_id
service_code
service_name
unit
quantity
unit_price
total_price
```

`unit_price` được lấy từ Pricing Service và lưu lại để bảng thanh toán không bị thay đổi khi bảng giá mới xuất hiện. Đây là phần đáp ứng PAY-03.

#### `payment_status_histories`

Lưu lịch sử xử lý:

```text
id
payment_board_id
action
from_status
status
actor_id
note
created_at
```

### 3.2. Bảng kỹ thuật

#### `payment_workflow_instances` và `payment_workflow_steps`

Lưu workflow phê duyệt, bước hiện tại và người được giao xử lý.

#### `payment_outbox_event`

Lưu event cần publish Kafka. Event chỉ được đánh dấu đã gửi sau khi Kafka nhận thành công.

#### `payment_idempotency_key`

Chống việc client gửi lại cùng một request tạo payment nhiều lần.

## 4. Luồng tạo bảng thanh toán

```mermaid
sequenceDiagram
    participant UI
    participant Payment
    participant Pricing
    participant Production
    participant DB

    UI->>Payment: POST /api/payments + JWT + payload
    Payment->>Pricing: POST /api/v1/payment-integration/validate-for-payment
    Pricing-->>Payment: is_valid + price version + unit prices
    Payment->>Production: GET /api/v1/volumes?customer_id&contract_id&period_key
    Production-->>Payment: danh sách volume
    Payment->>Payment: Kiểm tra volume tồn tại và is_locked=true
    Payment->>Payment: Snapshot quantity, unit, unit_price
    Payment->>DB: Lưu payment_board + payment_details + audit
    DB-->>Payment: Commit
    Payment-->>UI: Payment Board status=CALCULATED
```

### Request từ UI

UI gửi các field camelCase:

```json
{
  "customerId": "customer-id",
  "contractId": "contract-id",
  "priceTableId": "price-table-id",
  "periodStart": "2026-08-01",
  "periodEnd": "2026-08-31",
  "taxPercent": 10,
  "items": [
    {
      "serviceCode": "CONT",
      "serviceName": "Container handling",
      "unit": "container",
      "quantity": 100,
      "unitPrice": 50000
    }
  ]
}
```

Backend dùng Pydantic alias để map sang snake_case. Tuy nhiên `quantity`, `unit` và `unit_price` cuối cùng được lấy từ Pricing/Production, không tin hoàn toàn dữ liệu client gửi.

### Các bước kiểm tra

1. Kiểm tra `period_end >= period_start`.
2. Gọi Pricing Service để kiểm tra bảng giá.
3. Quy đổi kỳ thanh toán thành `period_key=YYYY-MM`, ví dụ `2026-08`.
4. Gọi Production Service lấy volume theo customer, contract và kỳ.
5. Từ chối nếu không có volume.
6. Từ chối nếu có volume chưa `is_locked=true`.
7. Đối chiếu service code giữa bảng giá, sản lượng và request.
8. Lấy đơn giá từ Pricing và sản lượng từ Production.
9. Tính:

```text
subtotal = tổng(quantity * unit_price)
tax_amount = subtotal * tax_percent / 100
total_amount = subtotal + tax_amount
```

10. Lưu payment cùng các dòng chi tiết và audit trong database.

## 5. Luồng gọi Pricing Service

### Endpoint hiện tại

```http
POST /api/v1/payment-integration/validate-for-payment
```

Trong Docker network, Payment gọi:

```text
http://pricing-service:8000/api/v1/payment-integration/validate-for-payment
```

### Request

```json
{
  "price_table_id": "PL-2026-003",
  "customer_id": "customer-id",
  "contract_id": "contract-id",
  "period_start": "2026-08-01",
  "period_end": "2026-08-31"
}
```

Payment forward JWT trong header `Authorization` nếu UI đã gửi token.

### Pricing kiểm tra

Pricing Service hiện kiểm tra:

- Bảng giá tồn tại theo UUID hoặc `price_list_code`.
- Bảng giá chưa bị xóa.
- Có version `EFFECTIVE`.
- `valid_from <= period_start`.
- `valid_to` là null hoặc `valid_to >= period_end`.
- Scope `CUSTOMER` khớp `customer_id`.
- Scope `CONTRACT` khớp `contract_id`.

### Response hợp lệ

```json
{
  "is_valid": true,
  "price_list_id": "uuid",
  "price_list_version_id": "uuid",
  "version_number": 1,
  "message": "Bảng giá hợp lệ để lập bảng thanh toán.",
  "items": [
    {
      "service_item_id": "uuid",
      "service_code": "CONT",
      "service_name": "Container handling",
      "unit": "container",
      "unit_price": 50000
    }
  ]
}
```

Nếu không hợp lệ, Payment trả lỗi nghiệp vụ `422` với nội dung `message` từ Pricing.

## 6. Luồng gọi Production Service

### Endpoint hiện tại

```http
GET /api/v1/volumes
```

Payment gọi:

```text
http://production-service:8000/api/v1/volumes
```

Query hiện tại:

```text
customer_id
contract_id
period_key
```

Ví dụ:

```text
/api/v1/volumes?customer_id=1&contract_id=1&period_key=2026-08
```

Payment tạo `period_key` từ `period_start`. Vì Production hiện dùng `period_key`, `period_start` và `period_end` phải nằm trong cùng một tháng.

### Production response hiện tại

Production trả danh sách volume, mỗi dòng có các field chính:

```json
{
  "id": 1,
  "customer_id": 1,
  "contract_id": 1,
  "service_code": "CONT",
  "period_key": "2026-08",
  "quantity": 100,
  "unit": "container",
  "is_locked": true
}
```

Production chưa có field `is_reconciled`. Trong Payment, quy ước hiện tại là:

```text
is_locked = true => sản lượng đã chốt/đối soát để tính payment
```

Nếu không có volume hoặc có volume chưa khóa, Payment trả `422` và không tạo hồ sơ.

Production yêu cầu JWT với một trong các role:

```text
OPERATION_STAFF
OPERATION_MANAGER
DIRECTOR
```

Vì vậy UI phải gửi:

```http
Authorization: Bearer <access_token>
```

Payment forward header này khi gọi Production.

## 7. Contract Service và PAY-01

PAY-01 yêu cầu kiểm tra:

- `contract_id` tồn tại.
- `customer_id` thuộc hợp đồng.
- Hợp đồng có trạng thái `ACTIVE`.
- Hợp đồng còn hiệu lực trong kỳ thanh toán.

Payment không tự truy cập database Contract Service. Payment cần gọi một API kiểu:

```http
GET /api/v1/contracts/{contract_id}/payment-validation?customer_id=...&period_start=...&period_end=...
```

Response mong muốn:

```json
{
  "valid": true,
  "contractId": "uuid",
  "customerId": "uuid",
  "status": "ACTIVE",
  "effectiveFrom": "2026-01-01",
  "effectiveTo": "2026-12-31"
}
```

Hiện Contract Service trong repository chỉ có `/`, nên luồng này chưa chạy được. Đây là phần teammate Contract cần cung cấp trước khi Payment có thể tích hợp PAY-01 đầy đủ.

## 8. Luồng trạng thái Payment Board

```mermaid
stateDiagram-v2
    [*] --> CALCULATED: tạo hồ sơ thành công
    CALCULATED --> RECONCILED: đối soát
    RECONCILED --> SUBMITTED: submit + tạo workflow
    SUBMITTED --> SUBMITTED: assignee bước hiện tại approve
    SUBMITTED --> APPROVED: assignee bước cuối approve
    SUBMITTED --> REJECTED: reject
    SUBMITTED --> REVISION_REQUESTED: request revision
    REVISION_REQUESTED --> CALCULATED: sửa lại hồ sơ
    APPROVED --> SIGNING: send-sign
    SIGNING --> SIGNED: callback success
    SIGNING --> SIGN_FAILED: callback failure
    SIGNING --> SIGN_CANCELLED: cancel-sign
    SIGN_FAILED --> SIGNING: gửi ký lại
    SIGN_CANCELLED --> SIGNING: gửi ký lại
    SIGNED --> ISSUED: issue
```

## 9. Luồng đối soát

1. Staff mở chi tiết payment ở trạng thái `CALCULATED`.
2. Staff gọi:

```http
POST /api/payments/{payment_id}/reconcile
```

3. Payment khóa row bằng transaction khi đổi trạng thái.
4. Payment cập nhật tổng tiền và ghi audit.
5. Payment tạo outbox event `payment.reconciled`.
6. Hồ sơ chuyển sang `RECONCILED`.

## 10. Luồng submit và workflow assignee

1. Staff gọi:

```http
POST /api/payments/{payment_id}/submit
```

2. Request phải có header:

```http
X-Approval-Assignees: user-a,user-b
```

3. Payment loại bỏ ID trùng và tạo workflow gồm các bước tuần tự.
4. Bước hiện tại là bước có `step_no = current_step`.
5. Chỉ `assignee_id` của bước hiện tại được xử lý.
6. Nếu approve sai người, API trả `403`.
7. Nếu còn bước tiếp theo, payment vẫn ở `SUBMITTED`.
8. Khi bước cuối approve, payment chuyển `APPROVED`.
9. Mọi hành động đều ghi audit và tạo outbox event.

Nếu không gửi `X-Approval-Assignees`, API trả `422`, không dùng fallback role chung.

## 11. Luồng từ chối hoặc yêu cầu sửa

Với các endpoint:

```http
POST /api/payments/{payment_id}/reject
POST /api/payments/{payment_id}/request-revision
```

request phải có comment:

```json
{
  "comment": "Thiếu chứng từ đối soát"
}
```

Nếu thiếu comment, API trả `422`.

- `REJECTED`: workflow kết thúc.
- `REVISION_REQUESTED`: hồ sơ được phép sửa lại.
- Sau khi sửa, payment quay về `CALCULATED` và có thể đối soát/submit lại.

## 12. Luồng khóa chỉnh sửa và adjustment

Payment chỉ cho sửa trực tiếp khi status thuộc:

```text
DRAFT
CALCULATED
RECONCILED
REVISION_REQUESTED
```

Payment không cho sửa trực tiếp khi hồ sơ đã:

```text
APPROVED
SIGNED
ISSUED
```

Nếu hồ sơ đã duyệt/ký/phát hành nhưng có sai sót, tạo hồ sơ điều chỉnh:

```http
POST /api/payments/{payment_id}/adjustment
```

Hồ sơ mới có:

```text
reference_id = id hồ sơ gốc
```

Hồ sơ điều chỉnh vẫn phải chạy validation Pricing và Production trước khi tạo.

## 13. Luồng ký điện tử mô phỏng

Sau khi workflow được duyệt hoàn tất:

```http
POST /api/payments/{payment_id}/send-sign
```

Payment chuyển:

```text
APPROVED -> SIGNING
```

Hệ thống mô phỏng callback:

```http
POST /api/payments/{payment_id}/sign-callback?success=true
```

Kết quả:

```text
SIGNING -> SIGNED
```

Nếu thất bại:

```text
SIGNING -> SIGN_FAILED
```

Có thể hủy phiên ký:

```http
POST /api/payments/{payment_id}/cancel-sign
```

Kết quả:

```text
SIGNING -> SIGN_CANCELLED
```

Sau khi ký thành công, phát hành hồ sơ:

```http
POST /api/payments/{payment_id}/issue
```

```text
SIGNED -> ISSUED
```

## 14. Audit log

Payment ghi audit ở các thao tác:

```text
CREATE
UPDATE
RECONCILE
SUBMIT
APPROVE
REJECT
REVISION
SEND_SIGN
SIGN_CALLBACK
CANCEL_SIGN
ISSUE
CREATE_ADJUSTMENT
```

Tra cứu lịch sử:

```http
GET /api/payments/{payment_id}/history
```

Ví dụ response:

```json
[
  {
    "action": "APPROVE",
    "fromStatus": "SUBMITTED",
    "status": "APPROVED",
    "actorId": "manager-01",
    "note": "Đã kiểm tra",
    "createdAt": "2026-08-27T10:00:00"
  }
]
```

## 15. Outbox và Kafka

Khi Payment thay đổi nghiệp vụ, event được lưu vào `payment_outbox_event` cùng transaction với dữ liệu payment.

Worker nền thực hiện:

1. Lấy các event có `published_at IS NULL`.
2. Tạo Kafka producer tới `kafka:29092`.
3. Gửi event với topic bằng `event_type`.
4. Nếu gửi thành công, cập nhật `published_at`.
5. Nếu Kafka lỗi, rollback và retry sau 2 giây.

Các event hiện có thể gồm:

```text
payment.reconciled
payment.submitted
payment.approved
payment.rejected
payment.revision_requested
payment.sign_requested
payment.signed
payment.sign_failed
payment.sign_cancelled
payment.issued
```

API kiểm tra event chưa publish:

```http
GET /api/payments/outbox/pending
```

Outbox giúp không mất event nếu database cập nhật thành công nhưng Kafka tạm thời unavailable.

## 16. Idempotency và race condition

### Idempotency khi tạo

Client có thể gửi:

```http
Idempotency-Key: unique-request-id
```

Nếu request được gửi lại với cùng key, Payment trả lại hồ sơ cũ thay vì tạo hồ sơ mới.

### Race condition khi approve

Payment dùng row-level lock:

```python
with_for_update()
```

Workflow step hiện tại cũng được khóa khi xử lý. Vì vậy hai request approve đồng thời không thể hoàn thành cùng một bước hai lần.

## 17. Các endpoint Payment chính

```text
GET    /
GET    /api/payments/stats
GET    /api/payments
POST   /api/payments
GET    /api/payments/{payment_id}
PUT    /api/payments/{payment_id}
POST   /api/payments/{payment_id}/reconcile
POST   /api/payments/{payment_id}/submit
POST   /api/payments/{payment_id}/approve
POST   /api/payments/{payment_id}/reject
POST   /api/payments/{payment_id}/request-revision
POST   /api/payments/{payment_id}/send-sign
POST   /api/payments/{payment_id}/sign-callback
POST   /api/payments/{payment_id}/cancel-sign
POST   /api/payments/{payment_id}/issue
POST   /api/payments/{payment_id}/adjustment
GET    /api/payments/{payment_id}/workflow
GET    /api/payments/{payment_id}/history
GET    /api/payments/outbox/pending
```

## 18. Các giới hạn hiện tại

- Contract Service chưa có API nghiệp vụ, nên PAY-01 chưa thể xác thực hợp đồng thật.
- Production đang dùng `period_key=YYYY-MM`, `customer_id`/`contract_id` kiểu Integer và yêu cầu JWT role nghiệp vụ.
- Production chưa có `is_reconciled`; Payment đang dùng `is_locked=true` làm điều kiện sản lượng đã chốt.
- Pricing response dùng `is_valid` và endpoint POST; Payment đã thích ứng theo format này.
- Backend JWT authorization riêng của Payment chưa triển khai; Payment hiện forward token sang upstream.
- Phiên ký điện tử hiện mô phỏng bằng callback, chưa có service ký bên ngoài.

## 19. Cách chạy và kiểm tra

Khởi động môi trường:

```powershell
docker compose up -d
```

Kiểm tra Payment:

```powershell
Invoke-RestMethod http://localhost:8085/
Invoke-RestMethod http://localhost:8085/api/payments/stats
```

Kiểm tra API Pricing:

```powershell
$body = @{price_table_id='PL-2026-003'; period_start='2026-08-01'; period_end='2026-08-31'} | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://localhost:8082/api/v1/payment-integration/validate-for-payment `
  -ContentType 'application/json' -Body $body
```

Kiểm tra API Production:

```powershell
Invoke-RestMethod 'http://localhost:8084/api/v1/volumes?customer_id=1&contract_id=1&period_key=2026-08' `
  -Headers @{Authorization='Bearer <access-token>'}
```

Kết quả payment chỉ hợp lệ khi Pricing trả bảng giá hợp lệ và Production trả sản lượng đã khóa.
