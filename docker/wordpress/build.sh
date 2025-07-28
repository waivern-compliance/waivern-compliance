#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
PULL_IMAGES=${PULL_IMAGES:-true}
CLEAN_BUILD=${CLEAN_BUILD:-false}

show_help() {
    cat << EOF
Waivern WordPress Docker Build Script

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -c, --clean         Clean build (remove existing images and volumes)
    --no-pull          Skip pulling latest images
    --pull-only        Only pull images, don't build anything custom

Environment Variables:
    PULL_IMAGES         Pull latest images (default: true)
    CLEAN_BUILD         Perform clean build (default: false)

Examples:
    $0                  # Standard build
    $0 --clean          # Clean build
    $0 --no-pull        # Build without pulling latest images
    
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--clean)
            CLEAN_BUILD=true
            shift
            ;;
        --no-pull)
            PULL_IMAGES=false
            shift
            ;;
        --pull-only)
            PULL_IMAGES=true
            PULL_ONLY=true
            shift
            ;;
        *)
            echo_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Change to script directory
cd "$SCRIPT_DIR"

main() {
    echo_info "🐳 Waivern WordPress Docker Build Script"
    echo_info "Working directory: $SCRIPT_DIR"
    
    # Check if Docker is running
    echo_step "Checking Docker availability..."
    if ! docker info >/dev/null 2>&1; then
        echo_error "Docker is not running or not accessible"
        exit 1
    fi
    echo_info "✅ Docker is available"
    
    # Check if Docker Compose is available
    if ! command -v docker compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
        echo_error "Docker Compose is not available"
        exit 1
    fi
    echo_info "✅ Docker Compose is available"
    
    # Clean build if requested
    if [ "$CLEAN_BUILD" = true ]; then
        echo_step "Performing clean build..."
        
        echo_info "Stopping and removing existing containers..."
        docker compose down --volumes --remove-orphans 2>/dev/null || true
        
        echo_info "Removing WordPress and MySQL images..."
        docker image rm wordpress:6.4-php8.2-apache 2>/dev/null || true
        docker image rm mysql:8.0 2>/dev/null || true
        
        echo_info "Pruning unused Docker resources..."
        docker system prune -f
        
        echo_info "✅ Clean build preparation complete"
    fi
    
    # Pull images if requested
    if [ "$PULL_IMAGES" = true ]; then
        echo_step "Pulling Docker images..."
        
        echo_info "Pulling MySQL 8.0 image..."
        docker pull mysql:8.0
        
        echo_info "Pulling WordPress 6.4-php8.2-apache image..."
        docker pull wordpress:6.4-php8.2-apache
        
        echo_info "✅ Image pulling complete"
        
        if [ "${PULL_ONLY:-false}" = true ]; then
            echo_info "Pull-only mode complete. Exiting."
            exit 0
        fi
    fi
    
    # Validate required files
    echo_step "Validating required files..."
    
    local required_files=(
        "docker-compose.yml"
        "scripts/entrypoint.sh"
        "seed-data/01-seed-data.sql"
    )
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo_error "Required file not found: $file"
            exit 1
        fi
        echo_info "✅ Found: $file"
    done
    
    # Validate entrypoint script is executable
    if [ ! -x "scripts/entrypoint.sh" ]; then
        echo_warn "Making entrypoint script executable..."
        chmod +x "scripts/entrypoint.sh"
    fi
    
    # Create plugins directory if it doesn't exist
    if [ ! -d "plugins" ]; then
        echo_info "Creating plugins directory..."
        mkdir -p plugins
        echo_info "✅ Created plugins directory"
    fi
    
    # Build/validate the compose setup
    echo_step "Validating Docker Compose configuration..."
    if docker compose config >/dev/null; then
        echo_info "✅ Docker Compose configuration is valid"
    else
        echo_error "Docker Compose configuration is invalid"
        exit 1
    fi
    
    # Create .env file with default values if it doesn't exist
    if [ ! -f ".env" ]; then
        echo_step "Creating default .env file..."
        cat > .env << EOF
# Waivern WordPress Docker Environment Configuration
# Generated on $(date)

# Port Configuration (use random ports for CI to avoid conflicts)
WORDPRESS_PORT=8080
MYSQL_PORT=3306

# WordPress Configuration
WP_URL=http://localhost:8080
WP_TITLE=Waivern Test Site
WP_ADMIN_USER=admin
WP_ADMIN_PASSWORD=admin123
WP_ADMIN_EMAIL=admin@testsite.com

# Force import demo content (set to true to reimport)
FORCE_IMPORT=false

# Build Configuration
PULL_IMAGES=true
CLEAN_BUILD=false
EOF
        echo_info "✅ Created .env file with default values"
        echo_warn "Review and modify .env file as needed for your environment"
    else
        echo_info "✅ Using existing .env file"
    fi
    
    echo_step "Build completed successfully! 🎉"
    echo_info ""
    echo_info "Next steps:"
    echo_info "  1. Review and modify .env file if needed"
    echo_info "  2. Run ./start.sh to start the WordPress environment"
    echo_info "  3. Access WordPress at http://localhost:8080"
    echo_info ""
    echo_info "Management commands:"
    echo_info "  ./start.sh    - Start WordPress containers"
    echo_info "  ./stop.sh     - Stop and clean up containers"
    echo_info "  ./build.sh    - Rebuild/update the environment"
}

# Run main function
main "$@" 