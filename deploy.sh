#!/bin/bash
# deploy.sh - Docker deployment script for GridTrader Pro

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"
}

# Configuration
PROJECT_NAME="gridtrader-pro"
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"

print_status "🚀 GridTrader Pro Docker Deployment"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

print_success "Docker and Docker Compose found"

# Check for environment file
if [ ! -f ".env.production" ]; then
    print_warning ".env.production not found, creating template..."
    
    cat > .env.production << 'EOF'
# GridTrader Pro Production Environment
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
ADMIN_TELEGRAM_ID=your_telegram_id_here
ENVIRONMENT=production
DATABASE_PATH=/app/data/gridtrader_clients.db
ENCRYPTION_KEY=your_32_character_encryption_key_here
LOG_LEVEL=INFO
EOF
    
    print_warning "Please edit .env.production with your actual values before deployment"
    print_status "Continuing with template values for now..."
fi

# Create necessary directories
print_status "Creating directories..."
mkdir -p data logs backups data/logs data/backups
print_success "Directories created"

# Check if there's a running container
if docker ps -q -f name=$PROJECT_NAME &> /dev/null; then
    print_status "Found running container, creating backup..."
    
    # Create backup directory
    mkdir -p $BACKUP_DIR
    
    # Backup database
    if [ -f "data/gridtrader_clients.db" ]; then
        cp data/gridtrader_clients.db $BACKUP_DIR/
        print_success "Database backed up to $BACKUP_DIR"
    fi
    
    # Stop existing container
    print_status "Stopping existing container..."
    docker-compose down
    print_success "Container stopped"
fi

# Build the image
print_status "Building Docker image..."
docker-compose build --no-cache
print_success "Image built successfully"

# Run tests before deployment
print_status "Running production tests in container..."
if docker-compose run --rm $PROJECT_NAME python3 final_fixed_test_runner.py; then
    print_success "All tests passed! ✅"
else
    print_error "Tests failed! Cannot deploy to production"
    exit 1
fi

# Deploy
print_status "Deploying to production..."
docker-compose up -d
print_success "Deployment complete!"

# Wait a moment for container to start
sleep 5

# Check container status
if docker ps -q -f name=$PROJECT_NAME &> /dev/null; then
    print_success "Container is running"
    
    # Show logs
    print_status "Recent logs:"
    docker-compose logs --tail=20 $PROJECT_NAME
    
    # Show container info
    print_status "Container status:"
    docker-compose ps
    
else
    print_error "Container failed to start"
    print_status "Checking logs..."
    docker-compose logs $PROJECT_NAME
    exit 1
fi

print_success "🎉 GridTrader Pro deployed successfully!"
echo ""
echo "📋 Management Commands:"
echo "  View logs:           docker-compose logs -f $PROJECT_NAME"
echo "  Stop service:        docker-compose down"
echo "  Restart service:     docker-compose restart"
echo "  Run tests:           docker-compose exec $PROJECT_NAME python3 final_fixed_test_runner.py"
echo "  Access container:    docker-compose exec $PROJECT_NAME bash"
echo "  View status:         docker-compose ps"
echo ""
echo "📊 Health check:       http://localhost:9090 (if monitoring enabled)"
echo "📁 Backups saved in:   $BACKUP_DIR"
