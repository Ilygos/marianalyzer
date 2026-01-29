#!/bin/bash
# Deploy Analyzer service to Cloud Run

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION=${REGION:-us-central1}

# Get Ollama service URL
OLLAMA_URL=$(gcloud run services describe ollama-qwen \
    --region=$REGION \
    --format='value(status.url)' \
    2>/dev/null || echo "")

if [ -z "$OLLAMA_URL" ]; then
    echo "Warning: Ollama service not found. Deploy it first with ./deploy-ollama.sh"
    echo "Or set OLLAMA_SERVICE_URL environment variable manually"
fi

echo "Deploying Analyzer service to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Ollama URL: $OLLAMA_URL"

# Build with additional env vars if Ollama URL is available
if [ -n "$OLLAMA_URL" ]; then
    EXTRA_VARS="--set-env-vars=OLLAMA_SERVICE_URL=$OLLAMA_URL,USE_CLOUD_RUN_AUTH=true"
else
    EXTRA_VARS=""
fi

# Submit build
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_REGION=$REGION \
    --project=$PROJECT_ID

# Update service with Ollama URL if available
if [ -n "$OLLAMA_URL" ]; then
    echo "Updating service with Ollama URL..."
    gcloud run services update analyzer \
        --region=$REGION \
        --set-env-vars=OLLAMA_SERVICE_URL=$OLLAMA_URL,USE_CLOUD_RUN_AUTH=true \
        --project=$PROJECT_ID
fi

echo "Deployment complete!"
echo ""
echo "Get service URL:"
echo "  gcloud run services describe analyzer --region=$REGION --format='value(status.url)'"
