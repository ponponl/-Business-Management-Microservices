# Contract Service

## 1. Khởi động Service

Đứng tại thư mục gốc của dự án (nơi chứa file `docker-compose.yml`) và chạy:

```bash
docker compose up -d --build contract-service
```

Hoặc chạy:

```bash
docker compose up -d --build
```

nếu muốn khởi động cùng lúc toàn bộ hệ thống.

---

## 2. Khởi tạo Cơ sở dữ liệu & Dữ liệu mẫu

> **Bắt buộc cho lần đầu**

Sau khi các container đã khởi động thành công, thực hiện 2 lệnh sau để tạo bảng và nạp dữ liệu mẫu.

### Bước 2.1: Chạy Migration để tạo Schema & Bảng

```bash
docker compose exec contract-service alembic upgrade head
```

### Bước 2.2: Seed dữ liệu khách hàng (Customer Data)

```bash
docker compose exec contract-service python seed_customer.py
```

---

## 3. Kiểm tra trạng thái & API Docs

### Swagger UI

[http://localhost:8083/docs](http://localhost:8083/docs)

### Health Check Endpoint

[http://localhost:8083/](http://localhost:8083/)

### Xem Log Outbox Publisher & Service

```bash
docker compose logs -f contract-service
```

---

## 4. Cấu hình Cổng & Môi trường kết nối

| Thành phần | Cấu hình |
|---|---|
| **Service Port** | `8083` |
| **Gateway** | `8080/api/v1/contracts` |
| **PostgreSQL Port** | `5433` |
| **Database** | `db_contract` |
| **PostgreSQL User** | `admin` |
| **PostgreSQL Password** | `password123` |
| **Kafka Internal Broker** | `kafka:29092` |
| **Topic sự kiện** | `contract.events` |
