#!/bin/bash

# Hawaii Appleseed Dashboard - Google Cloud Run Deployment Script

# Configuration variables
PROJECT_ID="your-gcp-project-id"  # Replace with your GCP project ID
SERVICE_NAME="hawaii-appleseed-dashboard"
REGION="us-central1"  # Change to your preferred region
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

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
    --memory 2Gi \
    --cpu 1 \
    --timeout 3600 \
    --max-instances 10 \
    --port 8080

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    echo "🌐 Your app should be available at the URL provided above"
else
    echo "❌ Deployment failed!"
    exit 1
fi
