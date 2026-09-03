# Deploy the complete stack to Minikube.
# Just run: .\deploy.ps1

$ErrorActionPreference = "Stop"
$profile = "business-management"
$namespace = "business-management"

if (-not (Get-Command minikube -ErrorAction SilentlyContinue)) { throw "minikube was not found in PATH. Install Minikube and Docker Desktop first." }
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) { throw "kubectl was not found in PATH. Install kubectl first." }

Write-Host "=== Starting Minikube profile: $profile ===" -ForegroundColor Green
minikube start --profile $profile --driver=docker --cpus=4 --memory=6144 --disk-size=40g
if ($LASTEXITCODE -ne 0) { throw "Minikube failed to start profile '$profile'." }
minikube update-context --profile $profile
if ($LASTEXITCODE -ne 0) { throw "Could not update kubectl context for profile '$profile'." }

Write-Host "=== Building images inside Minikube ===" -ForegroundColor Green
$services = @("auth_service", "contract_service", "payment_service", "notification_service", "production_service", "pricing_service")
foreach ($service in $services) {
	$image = $service.Replace("_", "-")
	minikube image build --profile $profile -t "${image}:latest" --file "Dockerfile.k8s" "services/$service"
	if ($LASTEXITCODE -ne 0) { throw "Image build failed for $image." }
	$imageList = minikube image ls --profile $profile
	if ($LASTEXITCODE -ne 0 -or -not ($imageList | Select-String -SimpleMatch "${image}:latest")) { throw "Image $image`:latest was not found in Minikube." }
}

Write-Host "=== Deploying to Minikube ===" -ForegroundColor Green
kubectl apply -f kubernetes/ -n $namespace
if ($LASTEXITCODE -ne 0) { throw "Kubernetes manifests could not be applied." }

Write-Host "=== Waiting for deployments ===" -ForegroundColor Green
kubectl wait --for=condition=available deployment --all -n $namespace --timeout=300s
if ($LASTEXITCODE -ne 0) {
	kubectl get pods -n $namespace -o wide
	throw "One or more deployments did not become available."
}
kubectl get pods -n $namespace

Write-Host ""
Write-Host "Gateway URL:" -ForegroundColor Cyan
minikube service api-gateway --profile $profile -n $namespace --url
