#!/bin/bash

# Corpus TE - Deploy to Hetzner VM Script
# This script automates the deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE_NAME="corpus-te-app"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_DIR="/opt/corpus-te"
BACKUP_DIR="/opt/corpus-te/backups"

echo -e "${GREEN}Starting Corpus TE Deployment...${NC}"

# Function to print colored output
print_step() {
    echo -e "${YELLOW}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if running as root or with sudo
if [[ $EUID -eq 0 ]]; then
    print_error "This script should not be run as root directly. Use a user with sudo privileges."
    exit 1
fi

# Check if we have sudo access
if ! sudo -n true 2>/dev/null; then
    print_error "This script requires sudo access. Please run with a user that has sudo privileges."
    exit 1
fi

# Create project directory
print_step "Creating project directory structure..."
sudo mkdir -p $PROJECT_DIR
sudo mkdir -p $BACKUP_DIR
sudo chown -R $USER:$USER $PROJECT_DIR

# Copy files to deployment directory
if [ -f "./$DOCKER_COMPOSE_FILE" ]; then
    print_step "Copying Docker Compose configuration..."
    cp $DOCKER_COMPOSE_FILE $PROJECT_DIR/
    print_success "Docker Compose file copied"
else
    print_error "Docker Compose file not found: $DOCKER_COMPOSE_FILE"
    exit 1
fi

# Copy environment file
if [ -f ".env" ]; then
    print_step "Copying environment configuration..."
    cp .env $PROJECT_DIR/
    print_success "Environment file copied"
else
    print_error "Environment file (.env) not found. Please create one based on .env.example"
    exit 1
fi

# Create uploads directory
mkdir -p $PROJECT_DIR/uploads
chmod 755 $PROJECT_DIR/uploads

# Change to project directory
cd $PROJECT_DIR

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

# Build Docker image if source files are available
if [ -f "Dockerfile" ]; then
    print_step "Building Docker image..."
    if docker build -t $DOCKER_IMAGE_NAME .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
elif ! docker image inspect $DOCKER_IMAGE_NAME >/dev/null 2>&1; then
    print_error "Docker image $DOCKER_IMAGE_NAME not found and no Dockerfile available."
    echo "Please ensure the source code is copied to the deployment directory."
    exit 1
else
    print_success "Docker image $DOCKER_IMAGE_NAME found locally"
fi

# Stop existing containers
print_step "Stopping existing containers..."
docker compose -f $DOCKER_COMPOSE_FILE down --remove-orphans

# Create database backup if containers exist
if docker ps --format "table {{.Names}}" | grep -q "postgres"; then
    print_step "Creating database backup..."
    BACKUP_FILE="$BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql"
    docker compose -f $DOCKER_COMPOSE_FILE exec -T postgres pg_dump -U postgres corpus_te > $BACKUP_FILE 2>/dev/null || true
    if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
        print_success "Database backup created: $BACKUP_FILE"
    else
        print_step "No existing database to backup or backup failed"
        rm -f "$BACKUP_FILE" 2>/dev/null || true
    fi
fi

# Start services (don't pull, use local images)
print_step "Starting services..."
docker compose -f $DOCKER_COMPOSE_FILE up -d --no-deps

# Wait for services to be healthy
print_step "Waiting for services to be ready..."
sleep 30

# Check service health
print_step "Checking service health..."

# Check if all services are running
if docker compose -f $DOCKER_COMPOSE_FILE ps | grep -q "unhealthy\|Exit"; then
    print_error "Some services are not healthy. Check logs with: docker compose -f $DOCKER_COMPOSE_FILE logs"
    exit 1
fi

# Test application endpoint
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_success "Application is responding"
else
    print_error "Application health check failed"
fi

# Show running services
print_step "Deployment completed! Running services:"
docker compose -f $DOCKER_COMPOSE_FILE ps

echo -e "${GREEN}"
echo "=============================================="
echo "  Corpus TE Deployment Successful!"
echo "=============================================="
echo "Application URL: http://your-server-ip:8000"
echo "Flower (Celery Monitor): http://your-server-ip:5555/flower"
echo "To view logs: docker compose -f $DOCKER_COMPOSE_FILE logs -f"
echo "To stop: docker compose -f $DOCKER_COMPOSE_FILE down"
echo -e "${NC}"
