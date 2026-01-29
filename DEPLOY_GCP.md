# GCP Deployment Guide

This guide explains how to deploy the Analyzer service to Google Cloud Platform (GCP) using Cloud Run.

## Architecture

The deployment consists of two Cloud Run services:

1. **Ollama Service** - GPU-enabled service running Ollama with Qwen 2.5 and Nomic embeddings
2. **Analyzer Service** - The main analyzer service with MCP tools exposed via HTTP API

```
┌─────────────────┐
│   Client/User   │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Analyzer Service    │  (Cloud Run)
│ - HTTP MCP Server   │
│ - SQLite + ChromaDB │
│ - Document parsers  │
└────────┬────────────┘
         │
         │ (IAM Auth)
         ▼
┌─────────────────────┐
│  Ollama Service     │  (Cloud Run + GPU)
│ - Qwen 2.5 7B       │
│ - Nomic Embeddings  │
└─────────────────────┘
```

## Prerequisites

1. **Google Cloud SDK** installed and configured
   ```bash
   gcloud --version
   ```

2. **Docker** installed (for local testing)
   ```bash
   docker --version
   ```

3. **GCP Project** with billing enabled
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

4. **Required APIs** enabled (done automatically by setup script)
   - Cloud Run API
   - Cloud Build API
   - Container Registry API
   - Cloud Storage API

## Quick Start

### 1. Initial Setup

Run the setup script to configure your GCP project:

```bash
./deploy/setup-gcp.sh
```

This script will:
- Enable required APIs
- Create a GCS bucket for document storage
- Set up service account permissions

### 2. Deploy Ollama Service

Deploy the GPU-enabled Ollama service:

```bash
./deploy/deploy-ollama.sh
```

This will:
- Build a Docker image with embedded Qwen 2.5 and Nomic models
- Deploy to Cloud Run with NVIDIA L4 GPU
- Configure for optimal GPU performance

**Note:** This deployment takes ~40 minutes due to large model downloads (7GB+).

Get the Ollama service URL:
```bash
gcloud run services describe ollama-qwen \
  --region=us-central1 \
  --format='value(status.url)'
```

### 3. Deploy Analyzer Service

Deploy the main analyzer service:

```bash
./deploy/deploy-analyzer.sh
```

This will:
- Build the analyzer Docker image
- Deploy to Cloud Run
- Automatically configure the Ollama service URL with IAM authentication

Get the Analyzer service URL:
```bash
gcloud run services describe analyzer \
  --region=us-central1 \
  --format='value(status.url)'
```

## Manual Deployment

If you prefer manual deployment or need custom configuration:

### Build and Deploy Ollama

```bash
# Build and push
gcloud builds submit \
  --config=cloudbuild-ollama.yaml \
  --substitutions=_REGION=us-central1

# Or manually
docker build -f Dockerfile.ollama -t gcr.io/PROJECT_ID/ollama-qwen .
docker push gcr.io/PROJECT_ID/ollama-qwen

gcloud run deploy ollama-qwen \
  --image=gcr.io/PROJECT_ID/ollama-qwen \
  --region=us-central1 \
  --gpu=1 \
  --gpu-type=nvidia-l4 \
  --cpu=8 \
  --memory=32Gi \
  --max-instances=1 \
  --concurrency=4 \
  --no-allow-unauthenticated
```

### Build and Deploy Analyzer

```bash
# Build and push
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_REGION=us-central1

# Or manually
docker build -t gcr.io/PROJECT_ID/analyzer .
docker push gcr.io/PROJECT_ID/analyzer

# Get Ollama URL
OLLAMA_URL=$(gcloud run services describe ollama-qwen \
  --region=us-central1 \
  --format='value(status.url)')

gcloud run deploy analyzer \
  --image=gcr.io/PROJECT_ID/analyzer \
  --region=us-central1 \
  --memory=2Gi \
  --cpu=2 \
  --max-instances=10 \
  --concurrency=80 \
  --no-allow-unauthenticated \
  --set-env-vars=OLLAMA_SERVICE_URL=$OLLAMA_URL,USE_CLOUD_RUN_AUTH=true
```

## Configuration

### Environment Variables

Set environment variables in Cloud Run console or via gcloud:

```bash
gcloud run services update analyzer \
  --region=us-central1 \
  --set-env-vars="
    GCP_PROJECT_ID=your-project-id,
    GCP_REGION=us-central1,
    OLLAMA_SERVICE_URL=https://ollama-qwen-xxx.run.app,
    USE_CLOUD_RUN_AUTH=true,
    GCS_BUCKET=your-bucket-name,
    USE_GCS=true,
    OLLAMA_LLM_MODEL=qwen2.5:7b-instruct,
    OLLAMA_EMBEDDING_MODEL=mxbai-embed-large:latest
  "
```

### Using GCS for Document Storage

Enable GCS storage:

```bash
gcloud run services update analyzer \
  --region=us-central1 \
  --set-env-vars="USE_GCS=true,GCS_BUCKET=your-bucket-name"
```

## Testing the Deployment

### 1. Test Ollama Service

```bash
OLLAMA_URL=$(gcloud run services describe ollama-qwen \
  --region=us-central1 \
  --format='value(status.url)')

# Get auth token
TOKEN=$(gcloud auth print-identity-token)

# Test generation
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:7b-instruct","prompt":"Hello!"}' \
  $OLLAMA_URL/api/generate
```

### 2. Test Analyzer Service

```bash
ANALYZER_URL=$(gcloud run services describe analyzer \
  --region=us-central1 \
  --format='value(status.url)')

TOKEN=$(gcloud auth print-identity-token)

# Health check
curl -H "Authorization: Bearer $TOKEN" $ANALYZER_URL/health

# List tools
curl -H "Authorization: Bearer $TOKEN" $ANALYZER_URL/tools
```

### 3. Test MCP Tools

```bash
# Get company playbook
curl -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id":"acme","doc_type":"offer_deck"}' \
  $ANALYZER_URL/tools/get_company_playbook
```

## Ingesting Documents

You can ingest documents using the CLI locally with Cloud Run backend:

```bash
# Install with GCP support
pip install -e .[gcp]

# Set environment variables
export OLLAMA_SERVICE_URL="https://ollama-qwen-xxx.run.app"
export USE_CLOUD_RUN_AUTH=true
export GCS_BUCKET="your-bucket-name"
export USE_GCS=true

# Run ingestion locally
analyzer process-all acme ./sample_data/acme --doc-type offer_deck
```

Or create a Cloud Run job for scheduled ingestion.

## Monitoring

### View Logs

```bash
# Analyzer logs
gcloud run services logs read analyzer --region=us-central1

# Ollama logs
gcloud run services logs read ollama-qwen --region=us-central1
```

### Monitor Metrics

View metrics in Cloud Console:
- Request count
- Request latency
- Error rate
- CPU/Memory utilization
- GPU utilization (for Ollama)

## Cost Optimization

### Ollama Service Costs

- **GPU (L4)**: ~$0.70/hour when running
- **Min instances: 0**: Scale to zero when not in use
- **Consider**: Use min-instances=1 for production to avoid cold starts (~2 min)

### Analyzer Service Costs

- **CPU/Memory**: ~$0.10/hour when running
- **Min instances: 0**: Scale to zero recommended
- **Requests**: $0.40 per million requests

### Tips

1. **Scale to zero** when not in production use
2. **Use smaller models** if possible (e.g., gemma2:2b)
3. **Batch requests** to reduce cold starts
4. **Monitor usage** with Cloud Billing reports

## Troubleshooting

### Ollama Service Issues

**Problem**: Service times out during deployment
- **Solution**: Increase build timeout in cloudbuild-ollama.yaml (default: 40 min)

**Problem**: GPU quota exceeded
- **Solution**: Request GPU quota increase in GCP Console

**Problem**: Model not loading
- **Solution**: Check that models are embedded in image: `docker run IMAGE ollama list`

### Analyzer Service Issues

**Problem**: Can't connect to Ollama
- **Solution**: Verify OLLAMA_SERVICE_URL and USE_CLOUD_RUN_AUTH=true

**Problem**: Authentication errors
- **Solution**: Ensure service account has `run.invoker` role on Ollama service

**Problem**: ChromaDB persistence issues
- **Solution**: Consider using Cloud SQL or mounting persistent volumes

## CI/CD Integration

### Using Cloud Build Triggers

Create a trigger for automatic deployment on git push:

```bash
gcloud builds triggers create github \
  --repo-name=your-repo \
  --repo-owner=your-org \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

### GitHub Actions

See `.github/workflows/deploy-gcp.yml` for GitHub Actions example.

## Security

1. **IAM Authentication**: Services require authentication by default
2. **Service-to-Service**: Analyzer uses IAM tokens to call Ollama
3. **Secrets Management**: Use Secret Manager for sensitive configs
4. **VPC**: Consider VPC connector for private networking

## Next Steps

1. Set up monitoring and alerting
2. Configure auto-scaling policies
3. Set up CI/CD pipelines
4. Enable Cloud SQL for production database
5. Implement caching layer (Memorystore)
6. Add load balancing for multiple regions

## Support

For issues or questions:
- Check logs: `gcloud run services logs read SERVICE_NAME`
- Review [Cloud Run documentation](https://cloud.google.com/run/docs)
- Review [Ollama Cloud Run tutorial](https://docs.cloud.google.com/run/docs/tutorials/gpu-gemma-with-ollama)
