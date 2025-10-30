# RAG API Deployment Guide

## Development
```bash
# Start development environment
docker-compose up -d

# Run locally
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Production with Dokploy

### 1. Dokploy Configuration (dokploy.yml)
- Auto-deployment from Git repository
- Redis service with persistence
- Resource limits and health checks
- Environment variable management

### 2. Docker Configuration
- **Dockerfile.prod**: Multi-stage production build with gunicorn
- **docker-compose.prod.yml**: Production orchestration with proper resource limits
- Security hardening with non-root user
- Health checks for both Redis and API

### 3. Key Features for Production
- **Gunicorn WSGI server** with 2 workers (configurable via WORKERS env var)
- **Redis persistence** with AOF and memory limits
- **Health monitoring** with automatic restarts
- **Resource constraints** to prevent OOM issues
- **Security hardening** with non-root execution

### 4. Environment Variables Required
```
OPENAI_API_KEY=your_openai_api_key
REDIS_URL=redis://redis:6379
WORKERS=2
```

### 5. API Endpoints
- `POST /prep-rag/` - Build/rebuild RAG corpus from website
- `POST /ask` - Query RAG with conversation history
- `GET /` - Health check

### 6. Deployment Verification
After deployment, verify:
1. Redis service is healthy: `redis-cli ping`
2. API responds: `curl http://your-domain/`
3. Corpus can be built: `POST /prep-rag/`
4. Questions work: `POST /ask`

The Docker setup is now fully aligned for Dokploy deployment with production-ready configurations.