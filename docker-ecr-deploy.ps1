# Run cmd: .\docker-ecr-deploy.ps1 -AWS_REGION "region" -AWS_ECR_REPO_URI "repo-uri" -AWS_ECR_IMAGE_TAG "docker-image-tag"
param (
    [string]$AWS_REGION,
    [string]$AWS_ECR_REPO_URI,
    [string]$AWS_ECR_IMAGE_TAG
)

# Ensure all required parameters are provided
if (-not $AWS_REGION -or -not $AWS_ECR_REPO_URI -or -not $AWS_ECR_IMAGE_TAG) {
    Write-Host "Error: Missing required parameters." -ForegroundColor Red
    Write-Host "Usage: .\docker-ecr-deploy.ps1 -AWS_REGION 'region' -AWS_ECR_REPO_URI 'repo-uri' -AWS_ECR_IMAGE_TAG 'docker-image-tag'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Logging into AWS ECR..." -ForegroundColor Cyan
# Log into ECR
docker login -u AWS -p $(aws ecr get-login-password --region $AWS_REGION) $AWS_ECR_REPO_URI

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to log into AWS ECR. Please check your AWS credentials and ECR repository URI." -ForegroundColor Red
    exit 1
}

Write-Host "Building Docker image with tag ${AWS_ECR_IMAGE_TAG}:latest..." -ForegroundColor Cyan
# Build Docker image
docker build -t "${AWS_ECR_IMAGE_TAG}:latest" .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to build Docker image. Please check your Dockerfile and build context." -ForegroundColor Red
    exit 1
}

Write-Host "Tagging Docker image for ECR..." -ForegroundColor Cyan
# Tag the image for ECR
docker tag "${AWS_ECR_IMAGE_TAG}:latest" "${AWS_ECR_REPO_URI}:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to tag Docker image. Please check your image name and ECR repository URI." -ForegroundColor Red
    exit 1
}

Write-Host "Pushing Docker image to AWS ECR..." -ForegroundColor Cyan
# Push the image to ECR
docker push "${AWS_ECR_REPO_URI}:latest"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to push Docker image to AWS ECR. Please check your network connection and ECR permissions." -ForegroundColor Red
    exit 1
}

Write-Host "Docker image deployed successfully to AWS ECR." -ForegroundColor Green
