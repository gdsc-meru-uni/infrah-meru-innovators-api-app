#!/bin/bash

# Enhanced Deployment Script for Azure Container Apps with Robust Error Handling and Logging

# Strict mode for better error handling
set -euo pipefail

# Define color codes for enhanced readability
declare -r YELLOW='\033[0;33m'
declare -r RED='\033[0;31m'
declare -r GREEN='\033[0;32m'
declare -r BLUE='\033[0;34m'
declare -r NC='\033[0m' # No Color

# Logging and error handling functions
log_error() {
    echo -e "${RED}[ERROR] $*${NC}" >&2
}

log_info() {
    echo -e "${BLUE}[INFO] $*${NC}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS] $*${NC}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING] $*${NC}"
}

# Error handler
handle_error() {
    local line_number=$1
    local command=$2
    log_error "Error occurred at line $line_number: $command"
    exit 1
}

# Trap errors
trap 'handle_error $LINENO "$BASH_COMMAND"' ERR

# Configuration and Initialization
initialize_configuration() {
    # Traverse up the directory tree to find globalenvdev.config
    local dir
    dir=$(pwd)
    while [[ "$dir" != "/" ]]; do
        if [[ -f "$dir/globalenvdev.config" ]]; then
            # shellcheck source=/dev/null
            source "$dir/globalenvdev.config"
            return 0
        fi
        dir=$(dirname "$dir")
    done

    log_error "globalenvdev.config not found"
    exit 1
}

# Validate required environment variables
validate_configuration() {
    local required_vars=(
        "ENVIRONMENT_PREFIX"
        "PROJECT_PREFIX"
        "PROJECT_LOCATION"
        "LOG_FOLDER"
        "PROJECT_RESOURCE_GROUP"
        "PROJECT_SUBSCRIPTION_ID"
    )

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable $var is not set"
            return 1
        fi
    done
}

# Azure authentication and subscription setup
setup_azure_context() {
    log_info "Checking Azure CLI authentication"
    
    # Login if not already authenticated
    if ! az account show &>/dev/null; then
        log_warning "Not logged in to Azure CLI. Initiating login..."
        az login
    fi

    # Set the target subscription
    log_info "Setting Azure subscription to ${PROJECT_SUBSCRIPTION_ID}"
    az account set --subscription "${PROJECT_SUBSCRIPTION_ID}"

    # Verify subscription is set correctly
    local current_subscription
    current_subscription=$(az account show --query id -o tsv)
    if [[ "$current_subscription" != "$PROJECT_SUBSCRIPTION_ID" ]]; then
        log_error "Failed to set Azure subscription. Current: $current_subscription, Expected: $PROJECT_SUBSCRIPTION_ID"
        return 1
    fi
}

# Prepare Azure Container Registry
prepare_container_registry() {
    local registry_name="${ENVIRONMENT_PREFIX}${PROJECT_PREFIX}contregistry"
    
    log_info "Checking Azure Container Registry: $registry_name"
    
    # Check if registry exists, create if not
    if ! az acr show --name "$registry_name" &>/dev/null; then
        log_warning "Container Registry does not exist. Creating..."
        az acr create \
            --name "$registry_name" \
            --resource-group "$PROJECT_RESOURCE_GROUP" \
            --sku Basic \
            --admin-enabled true
    fi

    # Login to ACR
    az acr login --name "$registry_name"
}

# Prepare Container Apps Environment
prepare_container_apps_environment() {
    local environment_name="${ENVIRONMENT_PREFIX}-${PROJECT_PREFIX}-BackendContainerAppsEnv"
    local container_app_name="${ENVIRONMENT_PREFIX}-${PROJECT_PREFIX}-worker"
    local registry_url="${ENVIRONMENT_PREFIX}${PROJECT_PREFIX}contregistry.azurecr.io"

    log_info "Preparing Container Apps Environment: $environment_name"

    # Create Container Apps Environment if not exists
    if ! az containerapp env show --name "$environment_name" --resource-group "$PROJECT_RESOURCE_GROUP" &>/dev/null; then
        log_warning "Container Apps Environment does not exist. Creating..."
        az containerapp env create \
            --name "$environment_name" \
            --resource-group "$PROJECT_RESOURCE_GROUP" \
            --location "$PROJECT_LOCATION"
    fi

    # Output environment and app details for reference
    echo "Environment Name: $environment_name"
    echo "Container App Name: $container_app_name"
    echo "Registry URL: $registry_url"
}

# Build and deploy container
deploy_container_app() {
    local environment_name="${ENVIRONMENT_PREFIX}-${PROJECT_PREFIX}-BackendContainerAppsEnv"
    local container_app_name="${ENVIRONMENT_PREFIX}-${PROJECT_PREFIX}-worker"
    local registry_url="${ENVIRONMENT_PREFIX}${PROJECT_PREFIX}contregistry.azurecr.io"
    local repo_url="https://github.com/gdsc-meru-uni/meru-innovators-infra-api"
    local branch="infrah-must-api-final"

    log_info "Deploying Container App: $container_app_name"

    # Deploy container app with valid parameters
    az containerapp up \
        --name "$container_app_name" \
        --resource-group "$PROJECT_RESOURCE_GROUP" \
        --environment "$environment_name" \
        --repo "$repo_url" \
        --branch "$branch" \
        --registry-server "$registry_url" \
        --ingress external \
        --target-port 8000


    # Update container app settings
    log_info "Configuring Container App scaling and resources"
    az containerapp update \
        --name "$container_app_name" \
        --resource-group "$PROJECT_RESOURCE_GROUP" \
        --cpu 0.25 \
        --memory 0.5Gi \
        --min-replicas 1 \
        --max-replicas 10

    # Optional: Disable public ingress if internal service
    # az containerapp ingress disable \
    #     --name "$container_app_name" \
    #     --resource-group "$PROJECT_RESOURCE_GROUP"
}

# Main deployment workflow
main() {
    # Configuration and setup must happen FIRST
    initialize_configuration
    validate_configuration

    # Now safe to use LOG_FOLDER
    local timestamp
    timestamp=$(date +"%Y%m%d_%H%M%S")
    local log_file="${LOG_FOLDER}/deploy_worker_${timestamp}.log"

    # Redirect output to log file and console
    exec > >(tee -a "$log_file") 2>&1

    log_info "Starting Container App Deployment Workflow"

    # Azure deployment steps
    setup_azure_context
    prepare_container_registry
    prepare_container_apps_environment
    deploy_container_app

    log_success "Deployment completed successfully"
    log_info "Detailed logs available at: $log_file"
}

# Execute main function with error handling
main "$@"