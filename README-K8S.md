# Kubernetes Setup - Simplified Version

## ✅ Setup Complete!

Kubernetes configuration cho dự án Business Management Microservices đã hoàn tất.

---

## 📦 Cấu trúc

### Kubernetes Manifests: 25 files
```
kubernetes/
├── 0-namespace.yaml                    # Namespace
├── 1-configmap.yaml                    # Configuration
├── 2-secrets.yaml                      # Passwords & keys
├── 3-5: postgres-*.yaml                # PostgreSQL (storage, deployment, service)
├── 6-8: redis-*.yaml                   # Redis (storage, deployment, service)
├── 9-10: kafka-*.yaml                  # Kafka + Zookeeper
├── 11-22: *-service-*.yaml             # 6 Microservices
├── 23-api-gateway-deployment.yaml      # Nginx Gateway
├── 24-nginx-configmap.yaml             # Nginx Config
└── 25-api-gateway-service.yaml         # LoadBalancer Service
```

### Dockerfiles: 6 files
```
services/*/Dockerfile.k8s       # Optimized for Kubernetes
```

---

## 🚀 Deploy (3 bước)

### 1. Build Docker Images
```bash
for service in auth_service contract_service payment_service notification_service production_service pricing_service; do
  docker build -f services/$service/Dockerfile.k8s -t ${service//_/-}:latest services/$service
done
```

### 2. Apply Kubernetes Manifests
```bash
kubectl apply -f kubernetes/
```

### 3. Check Status
```bash
kubectl get pods -n business-management
```

---

## 📊 Deployed Infrastructure

```
✅ Namespace: business-management
✅ PostgreSQL (1 pod, 10Gi)
✅ Redis (1 pod, 5Gi)
✅ Kafka (1 pod)
✅ Zookeeper (1 pod)
✅ 6 Microservices (2 pods each)
✅ Nginx API Gateway (2 pods, LoadBalancer)
```

**Total:** 17 pods, 19 services, 3 ConfigMaps, 2 Secrets

---

## 🌐 Access

```bash
# Minikube
minikube service api-gateway -n business-management

# Docker Desktop
curl http://localhost/api/v1/contracts/health

# Manual port forward
kubectl port-forward svc/api-gateway 8080:80 -n business-management
# Then: http://localhost:8080/api/v1/contracts
```

---

## 📝 View Logs

```bash
# From a pod
kubectl logs <pod-name> -n business-management

# Real-time
kubectl logs -f <pod-name> -n business-management

# From a service
kubectl logs -f -l app=auth-service -n business-management
```

---

## 🧹 Cleanup

```bash
kubectl delete namespace business-management
```

---

## 📚 Documentation

- **KUBERNETES.md** - Complete deployment guide with all commands

---

## 🔐 Before Production

Edit `kubernetes/2-secrets.yaml` and change:
```yaml
POSTGRES_PASSWORD: "secure-password"
JWT_SECRET: "secret-key-32-chars-min"
SMTP_PASSWORD: "your-password"
```

Then apply:
```bash
kubectl apply -f kubernetes/2-secrets.yaml
```

---

**Version:** 1.0  
**Status:** ✅ Ready to deploy  
**Size:** Lightweight, no Kustomize, no Ingress, no CI/CD, minimal logging
