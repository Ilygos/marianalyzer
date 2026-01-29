# GCP Cloud Run Adaptation - Summary

This document summarizes all changes made to adapt the Analyzer for Google Cloud Platform (GCP) deployment.

## Overview

The analyzer has been adapted to run on Google Cloud Run with the following architecture:

1. **Ollama Service** - GPU-enabled Cloud Run service running Ollama with embedded models
2. **Analyzer Service** - Main analyzer with HTTP MCP server
3. **Authentication** - IAM-based service-to-service communication
4. **Storage** - Optional GCS integration for document storage

## Files Created

### Docker & Deployment
- **Dockerfile** - Container definition for analyzer service
- **Dockerfile.ollama** - Container definition for GPU-enabled Ollama service
- **.dockerignore** - Docker build exclusions
- **cloudbuild.yaml** - Cloud Build configuration for analyzer
- **cloudbuild-ollama.yaml** - Cloud Build configuration for Ollama
- **deploy/setup-gcp.sh** - Initial GCP project setup script
- **deploy/deploy-ollama.sh** - Ollama service deployment script
- **deploy/deploy-analyzer.sh** - Analyzer service deployment script

### Code
- **src/analyzer/utils/gcp.py** - GCP authentication utilities
- **src/analyzer/store/gcs_store.py** - Google Cloud Storage adapter
- **src/analyzer/mcp/server_http.py** - HTTP MCP server using FastAPI

### Documentation
- **DEPLOY_GCP.md** - Comprehensive GCP deployment guide
- **GCP_CHANGES.md** - This file

## Files Modified

### Configuration
- **src/analyzer/config.py**
  - Added GCP-specific settings: `gcp_project_id`, `gcp_region`, `gcs_bucket`, `use_gcs`
  - Added Cloud Run settings: `ollama_service_url`, `use_cloud_run_auth`
  - Updated initialization to handle Cloud Run environment

- **pyproject.toml**
  - Added FastAPI and Uvicorn dependencies for HTTP server
  - Added optional `[gcp]` dependencies: google-cloud-storage, google-auth, etc.

- **.env.example**
  - Added GCP environment variable examples
  - Added Cloud Run configuration examples

### Code Updates
- **src/analyzer/utils/llm.py**
  - Updated `get_llm_client()` to support IAM authentication headers
  - Added Cloud Run authentication support

- **src/analyzer/store/__init__.py**
  - Added optional GCS store imports

- **README.md**
  - Added "Cloud-ready" feature highlight
  - Added GCP Deployment section with quick start guide
  - Added HTTP MCP server documentation
  - Added GCP configuration variables
  - Added GCP dependencies installation instructions

## Key Features

### 1. Dual Deployment Modes
- **Local**: Standard stdio MCP server with local Ollama
- **Cloud**: HTTP REST API with GPU-accelerated Cloud Run Ollama

### 2. IAM Authentication
- Service-to-service authentication using OIDC tokens
- Automatic token acquisition and header injection
- Secure communication between analyzer and Ollama services

### 3. Optional GCS Storage
- Google Cloud Storage adapter for document storage
- Seamless fallback to local filesystem
- Compatible with existing SQLite and ChromaDB stores

### 4. HTTP MCP Server
- FastAPI-based REST API exposing MCP tools
- Health check endpoints for Cloud Run
- CORS support for web clients
- Compatible with Cloud Run's HTTP/2 and gRPC requirements

### 5. Containerization
- Multi-stage Docker builds optimized for size
- Ollama container with pre-embedded models (7GB+)
- Proper health checks and signal handling

### 6. Infrastructure as Code
- Cloud Build configurations for CI/CD
- Deployment scripts with sensible defaults
- GPU configuration for Ollama (NVIDIA L4)
- Auto-scaling with scale-to-zero support

## Architecture Decisions

### Why Two Services?
- **Ollama Service**: Requires GPU (L4), expensive to run continuously
- **Analyzer Service**: CPU-only, cheaper to scale and keep running
- Separation allows independent scaling and cost optimization

### Why HTTP Instead of stdio?
- Cloud Run requires HTTP endpoints for health checks and requests
- HTTP allows multiple clients to access MCP tools simultaneously
- Compatible with Cloud Run's load balancing and auto-scaling

### Why Embed Models in Container?
- Faster cold starts (no model download on startup)
- More predictable latency
- Recommended by GCP for production deployments
- Trade-off: Larger container images (~8GB for Ollama)

### Why SQLite Instead of Cloud SQL?
- SQLite is fast and sufficient for MVP-1 scale
- Can be backed by persistent Cloud Run volumes
- Cloud SQL can be added later if needed
- Reduces complexity and cost for initial deployment

### Why Optional GCS?
- Local filesystem works well for smaller datasets
- GCS adds complexity and cost
- Allows gradual migration to cloud-native storage
- Future-proofs for multi-region deployments

## Cost Considerations

### Ollama Service (GPU)
- **Instance**: NVIDIA L4 GPU + 8 vCPU + 32GB RAM
- **Cost**: ~$0.70/hour when running
- **Scaling**: Scale to zero when idle (recommended for dev)
- **Production**: Consider min-instances=1 to avoid 2-min cold starts

### Analyzer Service (CPU)
- **Instance**: 2 vCPU + 2GB RAM
- **Cost**: ~$0.10/hour when running
- **Scaling**: Scale to zero recommended
- **Requests**: $0.40 per million requests

### Storage
- **GCS**: ~$0.02/GB/month for standard storage
- **ChromaDB/SQLite**: Stored in container volumes (included in instance cost)

### Typical Monthly Costs (Light Use)
- Ollama: $0-50 (if scaling to zero)
- Analyzer: $0-20 (if scaling to zero)
- GCS: $1-10 (depending on data size)
- **Total**: $1-80/month for development/light use

## Testing

### Local Testing
```bash
# Test with local Ollama
export OLLAMA_HOST=http://localhost:11434
python -m analyzer.mcp.server_http
```

### Cloud Testing
```bash
# Deploy both services
./deploy/setup-gcp.sh
./deploy/deploy-ollama.sh
./deploy/deploy-analyzer.sh

# Test endpoints
ANALYZER_URL=$(gcloud run services describe analyzer --region=us-central1 --format='value(status.url)')
TOKEN=$(gcloud auth print-identity-token)

curl -H "Authorization: Bearer $TOKEN" $ANALYZER_URL/health
curl -H "Authorization: Bearer $TOKEN" $ANALYZER_URL/tools
```

## Migration Path

### From Local to Cloud
1. Deploy Ollama service first (can take 40 minutes)
2. Test Ollama with simple prompts
3. Deploy analyzer service
4. Update analyzer to use Cloud Run Ollama URL
5. Test MCP tools via HTTP endpoints
6. (Optional) Enable GCS for document storage

### Rollback
- Services can be deleted without affecting local installation
- SQLite/ChromaDB data remains local unless migrated to GCS
- Local development continues to work unchanged

## Security

### Authentication
- All services require authentication by default
- IAM-based access control
- Service accounts with minimal permissions

### Network
- Services communicate over HTTPS
- Private service-to-service communication
- Optional VPC connector for full isolation

### Secrets
- Use Cloud Secret Manager for sensitive configs
- Never commit credentials to repository
- IAM handles service authentication automatically

## Monitoring & Operations

### Logs
```bash
gcloud run services logs read analyzer --region=us-central1
gcloud run services logs read ollama-qwen --region=us-central1
```

### Metrics
- Available in Cloud Console
- CPU, memory, request latency, error rates
- GPU utilization (for Ollama)
- Custom metrics can be added

### Alerts
- Set up Cloud Monitoring alerts for:
  - High error rates
  - High latency
  - GPU utilization
  - Cost thresholds

## Future Improvements

1. **Cloud SQL** - For multi-region or high-scale deployments
2. **Memorystore** - Redis cache for embeddings and frequently accessed data
3. **Multi-region** - Deploy to multiple regions for HA
4. **CI/CD** - GitHub Actions or Cloud Build triggers
5. **Secrets Manager** - For API keys and sensitive configs
6. **VPC** - Private networking between services
7. **CDN** - For static assets and caching
8. **Batch Processing** - Cloud Run Jobs for scheduled ingestion

## References

- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Ollama on Cloud Run Tutorial](https://docs.cloud.google.com/run/docs/tutorials/gpu-gemma-with-ollama)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MCP Specification](https://modelcontextprotocol.io/)

## Support

See [DEPLOY_GCP.md](DEPLOY_GCP.md) for detailed deployment instructions and troubleshooting.
