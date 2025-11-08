#!/bin/bash

# Kubernetes Copilot - Cloud Run Deployment Script
# This script deploys the K8s Copilot to Google Cloud Run

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="k8s-copilot"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo -e "${GREEN}=== Kubernetes Copilot - Cloud Run Deployment ===${NC}\n"

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: GOOGLE_CLOUD_PROJECT environment variable is not set${NC}"
    echo "Please set it with: export GOOGLE_CLOUD_PROJECT=your-project-id"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if API key is set
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${YELLOW}Warning: GOOGLE_API_KEY environment variable is not set${NC}"
    echo "You'll need to configure it later in Cloud Run"
fi

echo -e "${GREEN}Step 1: Setting up Google Cloud project${NC}"
gcloud config set project $PROJECT_ID

echo -e "\n${GREEN}Step 2: Enabling required APIs${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    monitoring.googleapis.com \
    logging.googleapis.com \
    container.googleapis.com

echo -e "\n${GREEN}Step 3: Building container image${NC}"
gcloud builds submit --tag ${IMAGE_NAME}

echo -e "\n${GREEN}Step 4: Creating service account${NC}"
SA_NAME="${SERVICE_NAME}-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if service account exists
if ! gcloud iam service-accounts describe ${SA_EMAIL} &> /dev/null; then
    gcloud iam service-accounts create ${SA_NAME} \
        --display-name="K8s Copilot Service Account"
fi

# Grant necessary permissions
echo -e "\n${GREEN}Step 5: Granting IAM permissions${NC}"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/logging.viewer"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/container.viewer"

echo -e "\n${GREEN}Step 6: Creating secret for API key${NC}"
if [ ! -z "$GOOGLE_API_KEY" ]; then
    echo -n "$GOOGLE_API_KEY" | gcloud secrets create google-api-key \
        --data-file=- \
        --replication-policy="automatic" 2>/dev/null || \
    echo -n "$GOOGLE_API_KEY" | gcloud secrets versions add google-api-key \
        --data-file=-

    # Grant secret access to service account
    gcloud secrets add-iam-policy-binding google-api-key \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/secretmanager.secretAccessor"
fi

echo -e "\n${GREEN}Step 7: Deploying to Cloud Run${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --service-account ${SA_EMAIL} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest"

echo -e "\n${GREEN}Deployment complete!${NC}"
echo -e "\n${YELLOW}Service URL:${NC}"
gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)'

echo -e "\n${YELLOW}Test the service with:${NC}"
echo "curl \$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')/health"
