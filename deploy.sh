#!/bin/bash

# Google Cloud Run deployment script for Slides Generator

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
REGION="${REGION:-europe-west4}"
SERVICE_NAME="slides-generator"

echo "Deploying Slides Generator to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com \
                      run.googleapis.com \
                      slides.googleapis.com \
                      drive.googleapis.com \
                      storage.googleapis.com

# Build and deploy using Cloud Build
echo "Building and deploying with Cloud Build..."
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.url)")

echo ""
echo "✅ Deployment completed!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📋 Next steps:"
echo "1. Set up service account with required permissions:"
echo "   - Slides API access"
echo "   - Drive API access"
echo "   - Storage access (if needed)"
echo ""
echo "2. Set environment variables if needed:"
echo "   gcloud run services update $SERVICE_NAME \\"
echo "     --region=$REGION \\"
echo "     --set-env-vars=\"OPENAI_API_KEY=your-key,GEMINI_API_KEY=your-key\""
echo ""
echo "3. Configure authentication if needed"