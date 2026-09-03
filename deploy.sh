#!/bin/bash
# Deploy the complete stack to Minikube.
# Just run: chmod +x deploy.sh && ./deploy.sh

set -euo pipefail

PROFILE="business-management"
NAMESPACE="business-management"

command -v minikube >/dev/null || { echo "minikube was not found in PATH"; exit 1; }
command -v kubectl >/dev/null || { echo "kubectl was not found in PATH"; exit 1; }

echo "=== Starting Minikube profile: ${PROFILE} ==="
minikube start --profile "${PROFILE}" --driver=docker --cpus=4 --memory=6144 --disk-size=40g
minikube update-context --profile "${PROFILE}"

echo "=== Building images inside Minikube ==="
for service in auth_service contract_service payment_service notification_service production_service pricing_service; do
	image="${service//_/-}"
	minikube image build --profile "${PROFILE}" -t "${image}:latest" --file "Dockerfile.k8s" "services/${service}"
done

echo "=== Deploying to Minikube ==="
kubectl apply -f kubernetes/ -n "${NAMESPACE}"

echo "=== Waiting for deployments to be available ==="
kubectl wait --for=condition=available deployment --all -n "${NAMESPACE}" --timeout=300s

kubectl get pods -n "${NAMESPACE}"

echo "Gateway URL:"
minikube service api-gateway --profile "${PROFILE}" -n "${NAMESPACE}" --url
