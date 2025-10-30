# PowerShell build test script for Windows
# Build and test script for the RAG API

Write-Host "🔨 Building Docker image with simple Dockerfile..." -ForegroundColor Green
docker build -f Dockerfile.simple -t rag-api:simple .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Simple build successful!" -ForegroundColor Green
    
    Write-Host "🔨 Building Docker image with production Dockerfile..." -ForegroundColor Green
    docker build -f Dockerfile.prod -t rag-api:prod .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Production build successful!" -ForegroundColor Green
        Write-Host "🚀 Both builds completed successfully!" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "To test locally:" -ForegroundColor Yellow
        Write-Host "docker-compose up -d" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To use production build in compose:" -ForegroundColor Yellow
        Write-Host "Update docker-compose.yml dockerfile to: Dockerfile.prod" -ForegroundColor Cyan
    } else {
        Write-Host "❌ Production build failed, but simple build works" -ForegroundColor Yellow
        Write-Host "Use Dockerfile.simple for deployment" -ForegroundColor Cyan
    }
} else {
    Write-Host "❌ Simple build failed - check requirements.txt and dependencies" -ForegroundColor Red
}