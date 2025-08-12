# Hawaii Appleseed Dashboard - Google Cloud Run Deployment

This guide will help you deploy the Hawaii Appleseed Dashboard to Google Cloud Run.

## Prerequisites

1. **Google Cloud SDK**: Install and configure the Google Cloud SDK
   ```bash
   # Install gcloud CLI (if not already installed)
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   ```

2. **Docker**: Ensure Docker is installed and running on your machine

3. **Google Cloud Project**: Create or select a GCP project with billing enabled

## Setup Steps

### 1. Configure Google Cloud Project

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Configure Docker for Google Container Registry

```bash
# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker
```

### 3. Update Configuration

Edit the `deploy.sh` file and replace `your-gcp-project-id` with your actual GCP project ID:

```bash
PROJECT_ID="your-actual-project-id"
```

### 4. Deploy the Application

Run the deployment script:

```bash
./deploy.sh
```

Or deploy manually:

```bash
# Build the Docker image
docker build -t gcr.io/$PROJECT_ID/hawaii-appleseed-dashboard .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/hawaii-appleseed-dashboard

# Deploy to Cloud Run
gcloud run deploy hawaii-appleseed-dashboard \
    --image gcr.io/$PROJECT_ID/hawaii-appleseed-dashboard \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 3600 \
    --max-instances 10 \
    --port 8080
```

## Configuration Options

### Resource Allocation
- **Memory**: 2Gi (recommended for geospatial data processing)
- **CPU**: 1 vCPU
- **Timeout**: 3600 seconds (1 hour)
- **Max Instances**: 10 (adjust based on expected traffic)

### Environment Variables
The following environment variables are automatically set:
- `STREAMLIT_SERVER_PORT=8080`
- `STREAMLIT_SERVER_ADDRESS=0.0.0.0`
- `STREAMLIT_SERVER_HEADLESS=true`
- `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`

## Troubleshooting

### Common Issues

1. **Build Failures**: Ensure all dependencies in `requirements.txt` are compatible
2. **Memory Issues**: Increase memory allocation if the app crashes due to large datasets
3. **Timeout Issues**: Increase timeout if data loading takes longer than expected

### Viewing Logs

```bash
# View recent logs
gcloud run services logs read hawaii-appleseed-dashboard --region=us-central1

# Follow logs in real-time
gcloud run services logs tail hawaii-appleseed-dashboard --region=us-central1
```

### Updating the Service

To update the deployed service, simply run the deployment script again:

```bash
./deploy.sh
```

## Cost Optimization

- Cloud Run charges only for actual usage
- Consider setting up auto-scaling based on traffic patterns
- Monitor usage through Google Cloud Console

## Security Considerations

- The service is deployed with `--allow-unauthenticated` for public access
- To restrict access, remove this flag and implement authentication
- Consider setting up a custom domain with SSL

## Support

For issues specific to the Hawaii Appleseed Dashboard, please refer to the main project documentation.
