# Parallel Minikube deploy script.
# Images are built in the Minikube runtime, so imagePullPolicy: Never works.

$ErrorActionPreference = "Stop"
$profile = "business-management"
$namespace = "business-management"
$workDir = (Get-Location).Path
$services = @("auth_service", "contract_service", "payment_service", "notification_service", "production_service", "pricing_service")

if (-not (Get-Command minikube -ErrorAction SilentlyContinue)) { throw "minikube was not found in PATH." }
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) { throw "kubectl was not found in PATH." }

Write-Host "=== Starting Minikube profile: $profile ===" -ForegroundColor Green
minikube start --profile $profile --driver=docker --cpus=4 --memory=6144 --disk-size=40g
if ($LASTEXITCODE -ne 0) { throw "Minikube failed to start profile '$profile'." }
minikube update-context --profile $profile
if ($LASTEXITCODE -ne 0) { throw "Could not update kubectl context for profile '$profile'." }

Write-Host "=== Building images inside Minikube ===" -ForegroundColor Green
$jobs = @()
foreach ($service in $services) {
    $image = $service.Replace("_", "-")
    $jobs += Start-Job -Name $image -ArgumentList $workDir, $profile, $image, $service -ScriptBlock {
        param($jobWorkDir, $jobProfile, $jobImage, $jobService)
        Set-Location $jobWorkDir
        minikube image build --profile $jobProfile -t "${jobImage}:latest" --file "Dockerfile.k8s" "services/$jobService"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
}
foreach ($job in $jobs) {
    $job | Wait-Job | Out-Null
    $job | Receive-Job
    if ($job.State -ne "Completed" -or $job.ChildJobs[0].JobStateInfo.State -ne "Completed") { throw "$($job.Name) image build failed." }
}
Remove-Job -Job $jobs

foreach ($service in $services) {
    $image = $service.Replace("_", "-")
    $imageList = minikube image ls --profile $profile
    if ($LASTEXITCODE -ne 0 -or -not ($imageList | Select-String -SimpleMatch "${image}:latest")) { throw "Image $image`:latest was not found in Minikube." }
}

Write-Host "=== Deploying to Minikube ===" -ForegroundColor Green
kubectl apply -f kubernetes/ -n $namespace
if ($LASTEXITCODE -ne 0) { throw "Kubernetes manifests could not be applied." }

Write-Host "=== Waiting for deployments to be available ===" -ForegroundColor Green
kubectl wait --for=condition=available deployment --all -n $namespace --timeout=300s
if ($LASTEXITCODE -ne 0) {
    kubectl get pods -n $namespace -o wide
    throw "One or more deployments did not become available."
}

kubectl get pods -n $namespace

Write-Host ""
Write-Host "Gateway URL:"
minikube service api-gateway --profile $profile -n $namespace --url
