#!/bin/bash
# CloudCopilot - Complete Setup Script
# Sets up all required GCP resources for the platform

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-hunt3r}"
REGION="${REGION:-europe-west1}"
REPOSITORY="cloudcopilot-repo"

echo "🚀 CloudCopilot Platform Setup"
echo "================================"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Set project
echo "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  container.googleapis.com \
  monitoring.googleapis.com \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com \
  cloudasset.googleapis.com \
  cloudbilling.googleapis.com \
  recommender.googleapis.com

# Create Artifact Registry repository
echo "Creating Artifact Registry repository..."
gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=$REGION \
  --description="CloudCopilot container images" \
  || echo "Repository already exists, continuing..."

# Create service accounts
echo "Creating service accounts..."

# K8s Copilot service account
gcloud iam service-accounts create k8s-copilot-sa \
  --display-name="K8s Copilot Service Account" \
  --description="Service account for K8s Copilot Cloud Run service" \
  || echo "k8s-copilot-sa already exists, continuing..."

# Cost Copilot service account
gcloud iam service-accounts create cost-copilot-sa \
  --display-name="Cost Copilot Service Account" \
  --description="Service account for Cost Copilot Cloud Run service" \
  || echo "cost-copilot-sa already exists, continuing..."

# Grant K8s Copilot permissions
echo "Granting K8s Copilot IAM permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:k8s-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:k8s-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"

# Grant Cost Copilot permissions
echo "Granting Cost Copilot IAM permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cost-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cost-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/compute.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cost-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cost-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/recommender.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cost-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/billing.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:cost-copilot-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectViewer"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create required secrets in Secret Manager:"
echo "   - GOOGLE_API_KEY (Gemini API key)"
echo "   - gke-kubeconfig (Kubernetes config with ServiceAccount token - for K8s Copilot)"
echo ""
echo "2. Deploy services:"
echo "   gcloud builds submit --config cloudbuild.yaml"
echo ""
echo "3. Access services at:"
echo "   - K8s Copilot: https://k8s-copilot-<hash>-${REGION}.run.app"
echo "   - Cost Copilot: https://cost-copilot-<hash>-${REGION}.run.app"
echo ""
