# 🚀 Quick Start - Kubernetes Deployment

## ⚡ Deploy trên Minikube

### 1. Cài công cụ (Windows)
Docker Desktop cần được cài và đang chạy trước khi dùng Docker driver.

```powershell
winget install Kubernetes.minikube
minikube version
```

Nếu máy chưa có `winget`, có thể cài bằng Chocolatey:

```powershell
choco install minikube
```

### 2. Khởi động Minikube
```bash
minikube start --profile business-management --driver=docker --cpus=4 --memory=6144 --disk-size=40g
```

### 3. Build và deploy
```bash
./deploy.sh
```

Windows PowerShell:
```powershell
.\deploy.ps1
```

Script sẽ dùng `minikube image build`, vì vậy image không bị kéo từ registry bên ngoài.

### 4. Chạy FE với Kubernetes
Terminal 1: giữ port-forward cố định chạy:

```powershell
kubectl port-forward service/api-gateway -n business-management 8090:80
```

Terminal 2: chạy FE bằng cấu hình Kubernetes:

```powershell
cd ui
npm run dev:kubernetes
```

FE sẽ dùng `http://localhost:8090`. Port `8090` được chọn để không đụng Docker Compose (`8080`) hoặc các service local (`8081`-`8087`).

### 5. Verify
```bash
kubectl get pods -n business-management
kubectl get svc -n business-management
```

### 6. Access
```bash
minikube service api-gateway --profile business-management -n business-management --url
```

---

## 📖 For More Details

See **KUBERNETES.md** for complete deployment guide.

---

**Time:** tùy tốc độ build image
**Files:** 25 YAML manifests  
**Resources:** PostgreSQL, Redis, Kafka, 6 Microservices, Nginx Gateway
