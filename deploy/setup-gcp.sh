#!/bin/bash
# Setup script for GCP deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Analyzer GCP Setup ===${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: No GCP project configured${NC}"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

REGION=${REGION:-us-central1}

echo -e "${YELLOW}Project ID: $PROJECT_ID${NC}"
echo -e "${YELLOW}Region: $REGION${NC}"

# Enable required APIs
echo -e "${GREEN}Enabling required APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    storage.googleapis.com \
    --project=$PROJECT_ID

# Create GCS bucket for documents (optional)
BUCKET_NAME="${PROJECT_ID}-analyzer-docs"
echo -e "${GREEN}Creating GCS bucket: $BUCKET_NAME${NC}"
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME/ 2>/dev/null || echo "Bucket already exists"

# Set up service accounts and permissions
echo -e "${GREEN}Setting up service accounts...${NC}"

# Get the Compute Engine default service account
SA_EMAIL="${PROJECT_ID}@appspot.gserviceaccount.com"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectAdmin" \
    --condition=None

echo -e "${GREEN}=== Setup Complete ===${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Deploy Ollama service: ./deploy/deploy-ollama.sh"
echo "2. Deploy Analyzer service: ./deploy/deploy-analyzer.sh"
echo "3. Set environment variables in Cloud Run console or update cloudbuild.yaml"
echo ""
echo -e "${YELLOW}Environment variables to set:${NC}"
echo "  - OLLAMA_SERVICE_URL: URL of the deployed Ollama service"
echo "  - GCS_BUCKET: $BUCKET_NAME (optional)"
echo "  - USE_GCS: true (optional)"
