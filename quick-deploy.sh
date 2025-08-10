#!/bin/bash
# Quick one-liner deployment for Azure Container Apps
# Simplest deployment with automatic image building

# Set your app name and resource group
export APP_NAME="${1:-starguide-api}"
export RG="${2:-rg-starguide}"

echo "🚀 Quick deploying $APP_NAME to Azure Container Apps..."

# Single command deployment - builds from source, creates everything needed
az containerapp up \
  --name $APP_NAME \
  --resource-group $RG \
  --location eastus \
  --source . \
  --ingress external \
  --target-port 8000 \
  --env-vars SE_EPHE_PATH=/app/ephe STARGUIDE_GEOCODER_USER_AGENT="StarGuide/1.0"

# Get and display the URL
URL="https://$(az containerapp show -n $APP_NAME -g $RG --query properties.configuration.ingress.fqdn -o tsv)"
echo "✅ App deployed to: $URL"
echo "📚 OpenAPI docs: $URL/docs"
echo "🏥 Health check: $URL/health"