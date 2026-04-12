#!/bin/bash

# Hawaii Appleseed Dashboard - Google Cloud Run Deployment Script
# NOTE: cloudbuild.yaml is the primary deployment method (via Cloud Build).
#       This script is for manual deploys and should stay in sync with cloudbuild.yaml.

# Configuration variables
PROJECT_ID="your-gcp-project-id"  # Replace with your GCP project ID
SERVICE_NAME="hi-data-dashboard"
REGION="us-west1"
IMAGE_NAME="us-west1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/hawaii-appleseed-dashboard/${SERVICE_NAME}"

echo "Deploying Hawaii Appleseed Dashboard to Google Cloud Run"
echo "Project ID: ${PROJECT_ID}"
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"

# Build the Docker image
echo "Building Docker image..."
docker build -t ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    echo "Docker build failed!"
    exit 1
fi

# Push the image to Artifact Registry
echo "Pushing image to Artifact Registry..."
docker push ${IMAGE_NAME}

if [ $? -ne 0 ]; then
    echo "Docker push failed!"
    exit 1
fi

# Deploy to Cloud Run (flags match cloudbuild.yaml)
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --port 8080 \
    --max-instances 3 \
    --min-instances 0 \
    --timeout 300s \
    --concurrency 10 \
    --no-cpu-throttling \
    --session-affinity

if [ $? -eq 0 ]; then
    echo "Deployment successful!"
    echo "Your app should be available at the URL provided above"
else
    echo "Deployment failed!"
    exit 1
fi
