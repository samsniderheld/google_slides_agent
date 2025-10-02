#!/bin/bash

# Google Cloud Run deployment script for Slides Generator

set -e

# Configuration
PROJECT_ID="monks-agentic-slides"
REGION="europe-west4"
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
# echo "Building and deploying to Cloud Run..."
# gcloud builds submit --config cloudbuild.yaml .

# Deploy directly to Cloud Run (simpler approach)
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --region=$REGION \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=900 \
  --concurrency=10 \
  --max-instances=100

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format="value(status.url)")

echo ""
echo "✅ Deployment completed!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📋 Next steps:"
echo "1. Grant access to your company domain:"
echo "   gcloud run services add-iam-policy-binding $SERVICE_NAME \\"
echo "     --region=$REGION \\"
echo "     --member='domain:monks.com' \\"
echo "     --role='roles/run.invoker'"
echo ""
echo "2. Set environment variables:"
echo "   gcloud run services update $SERVICE_NAME \\"
echo "     --region=$REGION \\"
echo "     --set-env-vars=\"GOOGLE_CLIENT_ID=your-id,GOOGLE_CLIENT_SECRET=your-secret,FLASK_SECRET_KEY=your-key,REDIRECT_URI=$SERVICE_URL/oauth2callback\""
echo ""
echo "3. Set up OAuth2 credentials in Google Cloud Console"