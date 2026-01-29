#!/bin/bash
# Deploy Ollama service to Cloud Run with GPU

set -e

PROJECT_ID=$(gcloud config get-value project)
REGION=${REGION:-us-central1}

echo "Deploying Ollama service to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Submit build
gcloud builds submit \
    --config=cloudbuild-ollama.yaml \
    --substitutions=_REGION=$REGION \
    --project=$PROJECT_ID

echo "Deployment complete!"
echo ""
echo "Get service URL:"
echo "  gcloud run services describe ollama-qwen --region=$REGION --format='value(status.url)'"
