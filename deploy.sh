#!/bin/bash

# Hawaii Appleseed Dashboard - Google Cloud Run Deployment Script

# Configuration variables
PROJECT_ID="composed-sensor-468822-i0"
SERVICE_NAME="hi-data-dashboard"
REGION="us-west1"
IMAGE_NAME="us-west1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/hawaii-appleseed-dashboard/hi-data-dashboard"

echo "🌴 Deploying Hawaii Appleseed Dashboard to Google Cloud Run"
echo "Project ID: ${PROJECT_ID}"
echo "Service Name: ${SERVICE_NAME}"
echo "Region: ${REGION}"

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t ${IMAGE_NAME} .

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

# Push the image to Google Container Registry
echo "🚀 Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}

if [ $? -ne 0 ]; then
    echo "❌ Docker push failed!"
    exit 1
fi

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 5 \
    --min-instances 1 \
    --concurrency 1 \
    --no-cpu-throttling \
    --port 8080

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🌐 Your app should be available at the URL provided above"
else
    echo "❌ Deployment failed!"
    exit 1
fi
