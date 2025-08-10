#!/bin/bash
# Azure Container Apps Deployment Script for FastAPI Service
# Production-ready deployment with HTTPS for GPT Actions

set -e  # Exit on error

# Configuration variables - customize these
RG="${RESOURCE_GROUP:-rg-starguide}"
APP="${APP_NAME:-starguide-api}"
LOC="${LOCATION:-eastus}"
ENV_NAME="${ENVIRONMENT:-starguide-env}"
ACR_NAME="${ACR_NAME:-starguideacr$RANDOM}"

# Color output for clarity
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Azure Container Apps FastAPI Deployment Script${NC}"
echo "================================================"

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"
if ! command -v az &> /dev/null; then
    echo -e "${RED}Azure CLI not found. Please install: https://aka.ms/installazurecli${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}Docker not found. Using 'az containerapp up' for source-based deployment.${NC}"
    USE_SOURCE_DEPLOY=true
else
    USE_SOURCE_DEPLOY=false
fi

# Login check
echo -e "\n${YELLOW}Checking Azure login...${NC}"
if ! az account show &> /dev/null; then
    echo "Please login to Azure:"
    az login
fi

# Display current subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}Using subscription: $SUBSCRIPTION${NC}"

# Install/update Container Apps extension
echo -e "\n${YELLOW}Installing/updating Container Apps extension...${NC}"
az extension add --name containerapp --upgrade -y

# Create resource group
echo -e "\n${YELLOW}Creating resource group...${NC}"
az group create --name $RG --location $LOC --output table

# Deployment method selection
if [ "$USE_SOURCE_DEPLOY" = true ]; then
    echo -e "\n${GREEN}Deploying from source (no Docker required)...${NC}"
    
    # Deploy directly from source - Azure builds the container
    az containerapp up \
        --name $APP \
        --resource-group $RG \
        --location $LOC \
        --source . \
        --ingress external \
        --target-port 8000 \
        --env-vars \
            SE_EPHE_PATH=/app/ephe \
            STARGUIDE_GEOCODER_USER_AGENT="StarGuide/1.0" \
            ENVIRONMENT=production
    
else
    echo -e "\n${GREEN}Using Docker build and Azure Container Registry...${NC}"
    
    # Create ACR if it doesn't exist
    echo -e "\n${YELLOW}Creating Azure Container Registry...${NC}"
    az acr create \
        --resource-group $RG \
        --name $ACR_NAME \
        --sku Basic \
        --admin-enabled true \
        --output table
    
    # Get ACR login server
    LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
    echo -e "${GREEN}ACR Login Server: $LOGIN_SERVER${NC}"
    
    # Build and push Docker image
    echo -e "\n${YELLOW}Building Docker image...${NC}"
    docker build -t $LOGIN_SERVER/starguide:latest .
    
    echo -e "\n${YELLOW}Logging into ACR...${NC}"
    az acr login --name $ACR_NAME
    
    echo -e "\n${YELLOW}Pushing image to ACR...${NC}"
    docker push $LOGIN_SERVER/starguide:latest
    
    # Create Container Apps environment if it doesn't exist
    echo -e "\n${YELLOW}Creating Container Apps environment...${NC}"
    az containerapp env create \
        --name $ENV_NAME \
        --resource-group $RG \
        --location $LOC \
        --output table
    
    # Deploy container app
    echo -e "\n${YELLOW}Deploying Container App...${NC}"
    az containerapp create \
        --name $APP \
        --resource-group $RG \
        --environment $ENV_NAME \
        --image $LOGIN_SERVER/starguide:latest \
        --ingress external \
        --target-port 8000 \
        --registry-server $LOGIN_SERVER \
        --registry-username $(az acr credential show --name $ACR_NAME --query username -o tsv) \
        --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
        --env-vars \
            SE_EPHE_PATH=/app/ephe \
            STARGUIDE_GEOCODER_USER_AGENT="StarGuide/1.0" \
            ENVIRONMENT=production \
        --cpu 0.5 \
        --memory 1.0 \
        --min-replicas 1 \
        --max-replicas 3 \
        --output table
fi

# Get the public URL
echo -e "\n${YELLOW}Getting application URL...${NC}"
APP_URL=$(az containerapp show \
    --name $APP \
    --resource-group $RG \
    --query properties.configuration.ingress.fqdn \
    -o tsv)

FULL_URL="https://$APP_URL"

echo -e "\n${GREEN}✅ Deployment Complete!${NC}"
echo "=================================="
echo -e "${GREEN}Your FastAPI app is available at:${NC}"
echo -e "${YELLOW}$FULL_URL${NC}"
echo ""
echo -e "${GREEN}OpenAPI Documentation:${NC}"
echo -e "${YELLOW}$FULL_URL/docs${NC}"
echo ""
echo -e "${GREEN}Health Check Endpoint:${NC}"
echo -e "${YELLOW}$FULL_URL/health${NC}"
echo ""

# Test the health endpoint
echo -e "\n${YELLOW}Testing health endpoint...${NC}"
if curl -s "$FULL_URL/health" | grep -q "healthy"; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check didn't return expected response. The app may still be starting up.${NC}"
fi

# Display GPT Actions configuration
echo -e "\n${GREEN}For GPT Actions Configuration:${NC}"
echo "=================================="
echo "Add this to your OpenAPI spec servers list:"
echo ""
echo "servers:"
echo "  - url: $FULL_URL"
echo "    description: Production Azure Container Apps"
echo ""

# Optional: Custom domain setup
echo -e "\n${YELLOW}Optional: To add a custom domain (e.g., api.yourdomain.com):${NC}"
echo "1. Add CNAME record pointing to: $APP_URL"
echo "2. Run: az containerapp hostname add -g $RG -n $APP --hostname api.yourdomain.com"
echo "3. Run: az containerapp hostname bind -g $RG -n $APP --hostname api.yourdomain.com --certificate managed"

# Monitoring commands
echo -e "\n${GREEN}Useful monitoring commands:${NC}"
echo "View logs:        az containerapp logs show -g $RG -n $APP --follow"
echo "Check ingress:    az containerapp ingress show -g $RG -n $APP"
echo "Update app:       az containerapp update -g $RG -n $APP --set-env-vars KEY=value"
echo "Scale app:        az containerapp update -g $RG -n $APP --min-replicas 2 --max-replicas 10"
echo ""

# Cleanup command
echo -e "${YELLOW}To delete all resources:${NC}"
echo "az group delete --name $RG --yes --no-wait"