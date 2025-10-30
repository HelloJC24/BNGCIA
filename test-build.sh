#!/bin/bash
# Build and test script for the RAG API

echo "🔨 Building Docker image with simple Dockerfile..."
docker build -f Dockerfile.simple -t rag-api:simple .

if [ $? -eq 0 ]; then
    echo "✅ Simple build successful!"
    
    echo "🔨 Building Docker image with production Dockerfile..."
    docker build -f Dockerfile.prod -t rag-api:prod .
    
    if [ $? -eq 0 ]; then
        echo "✅ Production build successful!"
        echo "🚀 Both builds completed successfully!"
        
        echo ""
        echo "To test locally:"
        echo "docker-compose up -d"
        echo ""
        echo "To use production build in compose:"
        echo "Update docker-compose.yml dockerfile to: Dockerfile.prod"
    else
        echo "❌ Production build failed, but simple build works"
        echo "Use Dockerfile.simple for deployment"
    fi
else
    echo "❌ Simple build failed - check requirements.txt and dependencies"
fi