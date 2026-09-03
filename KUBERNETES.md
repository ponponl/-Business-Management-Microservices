# Kubernetes Deployment Guide - Business Management Microservices

Hướng dẫn triển khai Business Management Microservices trên Kubernetes (gọn nhẹ).

## 📋 Yêu cầu

### Công cụ cần cài:
- **Docker Desktop** - Minikube Docker driver and base images
- **kubectl** - Quản lý Kubernetes
- **Minikube** (bắt buộc cho setup này)

### Cài đặt:

**Windows:**
```powershell
# Cài Docker Desktop (kèm kubectl)
# https://www.docker.com/products/docker-desktop

# Cài Minikube bằng Windows Package Manager
winget install Kubernetes.minikube

# Kiểm tra sau khi cài
minikube version

# Nếu máy không có winget, dùng Chocolatey thay thế
# choco install minikube
```

**Linux/macOS:**
```bash
brew install docker kubectl minikube
```

---

## 🚀 Triển khai trên Minikube

### Bước 1: Khởi động Kubernetes Cluster

```bash
minikube start --profile business-management --driver=docker --cpus=4 --memory=6144 --disk-size=40g
```
minikube start -p business-management
### Bước 2: Build và deploy

```bash
./deploy.sh
```

Windows PowerShell:
```powershell
.\deploy.ps1
```

Script tự build image trong Minikube, apply manifests và chờ tất cả deployment available. Không cần chạy `eval $(minikube docker-env)`.

### Deploy thủ công từng bước

1. Tạo namespace:
```bash
kubectl apply -f kubernetes/0-namespace.yaml
```

2. Tạo config & secrets:
```bash
kubectl apply -f kubernetes/1-configmap.yaml
kubectl apply -f kubernetes/2-secrets.yaml
```

3. Deploy databases:
```bash
kubectl apply -f kubernetes/3-postgres-pvc.yaml
kubectl apply -f kubernetes/4-postgres-deployment.yaml
kubectl apply -f kubernetes/5-postgres-service.yaml

kubectl apply -f kubernetes/6-redis-pvc.yaml
kubectl apply -f kubernetes/7-redis-deployment.yaml
kubectl apply -f kubernetes/8-redis-service.yaml
```

4. Deploy message queue:
```bash
kubectl apply -f kubernetes/9-kafka-deployment.yaml
kubectl apply -f kubernetes/10-kafka-service.yaml
```

5. Deploy microservices:
```bash
kubectl apply -f kubernetes/11-auth-service-deployment.yaml
kubectl apply -f kubernetes/12-auth-service.yaml
kubectl apply -f kubernetes/13-contract-service-deployment.yaml
kubectl apply -f kubernetes/14-contract-service.yaml
kubectl apply -f kubernetes/15-payment-service-deployment.yaml
kubectl apply -f kubernetes/16-payment-service.yaml
kubectl apply -f kubernetes/17-notification-service-deployment.yaml
kubectl apply -f kubernetes/18-notification-service.yaml
kubectl apply -f kubernetes/19-production-service-deployment.yaml
kubectl apply -f kubernetes/20-production-service.yaml
kubectl apply -f kubernetes/21-pricing-service-deployment.yaml
kubectl apply -f kubernetes/22-pricing-service.yaml
```

6. Deploy API Gateway:
```bash
kubectl apply -f kubernetes/24-nginx-configmap.yaml
kubectl apply -f kubernetes/23-api-gateway-deployment.yaml
kubectl apply -f kubernetes/25-api-gateway-service.yaml
```

### Bước 4: Kiểm tra trạng thái

```bash
# Xem pods
kubectl get pods -n business-management

# Xem services
kubectl get svc -n business-management

# Xem persistent volumes
kubectl get pvc -n business-management
```

---

## 📊 Infrastructure Deployed

| Component | Qty | Replicas | Port | Storage |
|-----------|-----|----------|------|---------|
| PostgreSQL | 1 | 1 | 5432 | 10Gi |
| Redis | 1 | 1 | 6379 | 5Gi |
| Kafka | 1 | 1 | 9092 | - |
| Zookeeper | 1 | 1 | 2181 | - |
| Auth Service | 1 | 2 | 8001 | - |
| Contract Service | 1 | 2 | 8002 | - |
| Payment Service | 1 | 2 | 8003 | - |
| Notification Service | 1 | 2 | 8004 | - |
| Production Service | 1 | 2 | 8005 | - |
| Pricing Service | 1 | 2 | 8006 | - |
| API Gateway (Nginx) | 1 | 2 | 80 | - |

**Total:** 11 deployments, 2 replicas per service, 15Gi storage

---

## 🌐 Truy cập ứng dụng

### Qua Minikube:
```bash
minikube service api-gateway --profile business-management -n business-management --url
```

### Port forwarding:
```bash
kubectl port-forward svc/api-gateway 8080:80 -n business-management
# Truy cập: http://localhost:8080/api/v1/contracts
```

---

## 📝 Logging & Monitoring

### View logs
```bash
# Logs từ một pod
kubectl logs <pod-name> -n business-management

# Logs real-time
kubectl logs -f <pod-name> -n business-management

# Logs từ một service
kubectl logs -f -l app=auth-service -n business-management
```

Services log to **stdout** - dễ dàng xem bằng `kubectl logs`.

---

## 🔍 Các lệnh kubectl thường dùng

### Debugging
```bash
# SSH vào pod
kubectl exec -it <pod-name> -n business-management -- sh

# Describe pod
kubectl describe pod <pod-name> -n business-management

# Xem environment variables
kubectl exec -it <pod-name> -n business-management -- env
```

### Networking
```bash
# Port forward để test local
kubectl port-forward svc/auth-service 8001:8001 -n business-management

# Test service connectivity
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  wget -O- http://auth-service.business-management.svc.cluster.local:8001/health
```

### Scaling
```bash
# Scale up
kubectl scale deployment auth-service --replicas=3 -n business-management

# View deployment status
kubectl get deployment -n business-management
```

---

## 🔧 Thay đổi Configuration

### Đổi Secrets (Passwords)

Edit `kubernetes/2-secrets.yaml`:

```yaml
stringData:
  POSTGRES_PASSWORD: "your-secure-password"
  JWT_SECRET: "your-secret-key-min-32-chars"
```

Apply:
```bash
kubectl apply -f kubernetes/2-secrets.yaml
```

### Đổi Environment Variables

Edit `kubernetes/1-configmap.yaml`:

```yaml
data:
  LOG_LEVEL: "INFO"
  REDIS_HOST: "redis-service.business-management.svc.cluster.local"
```

Apply:
```bash
kubectl apply -f kubernetes/1-configmap.yaml
```

### Đổi số replicas

Edit deployment file (e.g., `kubernetes/11-auth-service-deployment.yaml`):

```yaml
spec:
  replicas: 3
```

Apply:
```bash
kubectl apply -f kubernetes/11-auth-service-deployment.yaml
```

---

## 🧹 Dọn dẹp

### Xóa toàn bộ namespace:
```bash
kubectl delete namespace business-management
```

### Xóa từng file:
```bash
kubectl delete -f kubernetes/
```

### Dừng Minikube:
```bash
minikube stop
minikube delete
```

---

## 🆘 Troubleshooting

### Pods không start
```bash
kubectl describe pod <pod-name> -n business-management
kubectl logs <pod-name> -n business-management
```

**Nguyên nhân:** Image không tìm, resource không đủ, dependencies chưa ready.

### Service không accessible
```bash
# Kiểm tra service tồn tại
kubectl get endpoints -n business-management

# Test từ pod khác
kubectl run -it --rm test --image=busybox --restart=Never -- \
  wget -O- http://auth-service.business-management.svc.cluster.local:8001/health
```

### Database connection failed
```bash
# Kiểm tra PostgreSQL
kubectl logs postgres-<pod-id> -n business-management

# Test connection
kubectl run -it --rm pgtest --image=postgres:15 --restart=Never -- \
  psql -h postgres-service -U postgres -c "SELECT 1"
```

### Storage issues
```bash
kubectl get pvc -n business-management
kubectl describe pvc postgres-pvc -n business-management
```

---

## 📊 Kubernetes Files

```
kubernetes/
├── 0-namespace.yaml
├── 1-configmap.yaml
├── 2-secrets.yaml
├── 3-5: postgres-pvc, deployment, service
├── 6-8: redis-pvc, deployment, service
├── 9-10: kafka-deployment, service
├── 11-22: 6 microservices (deployment + service each)
├── 23-24-25: api-gateway (deployment, config, service)
└── Total: 25 YAML files
```

---

## ✅ Checklist

- [ ] Docker & kubectl installed
- [ ] Kubernetes cluster running
- [ ] Build all images
- [ ] Apply kubernetes/ YAML files
- [ ] All pods running
- [ ] All services have IP
- [ ] API Gateway accessible
- [ ] Health checks passing

---

## 📈 Resource Requirements

**Minimum:**
```
CPU: 3.5 cores
Memory: 3.5 GB  
Storage: 15 Gi
```

---

## 🔐 Default Secrets (Change before production!)

```
POSTGRES_PASSWORD: postgres_password_123
JWT_SECRET: your-secret-key-change-in-production...
SMTP_PASSWORD: your-email-password
```

---

## 📚 References

- [Kubernetes Docs](https://kubernetes.io/docs/)
- [Kubectl Cheatsheet](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)
- [Minikube Docs](https://minikube.sigs.k8s.io/)

---

**Version:** 1.0  
**Updated:** 2026-08-31
