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
DETACHED=${DETACHED:-true}
WAIT_FOR_READY=${WAIT_FOR_READY:-true}
SHOW_LOGS=${SHOW_LOGS:-false}

show_help() {
    cat << EOF
Waivern WordPress Docker Start Script

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -f, --foreground    Run in foreground (not detached)
    --no-wait          Don't wait for services to be ready
    --logs             Show logs after starting
    --rebuild          Rebuild containers before starting

Environment Variables:
    WORDPRESS_PORT      WordPress port (default: 8080)
    MYSQL_PORT         MySQL port (default: 3306)
    DETACHED           Run in background (default: true)
    WAIT_FOR_READY     Wait for services (default: true)

Examples:
    $0                  # Standard start (detached)
    $0 --foreground     # Run in foreground
    $0 --logs           # Start and show logs
    $0 --rebuild        # Rebuild and start

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--foreground)
            DETACHED=false
            shift
            ;;
        --no-wait)
            WAIT_FOR_READY=false
            shift
            ;;
        --logs)
            SHOW_LOGS=true
            shift
            ;;
        --rebuild)
            REBUILD=true
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

wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=${3:-60}

    echo_info "Waiting for $service_name to be ready..."
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" >/dev/null 2>&1; then
            echo_info "✅ $service_name is ready!"
            return 0
        fi

        if [ $((attempt % 10)) -eq 0 ]; then
            echo_info "Still waiting for $service_name... (attempt $attempt/$max_attempts)"
        fi

        sleep 2
        ((attempt++))
    done

    echo_error "❌ $service_name failed to become ready after $max_attempts attempts"
    return 1
}

check_port_availability() {
    local port=$1
    local service_name=$2

    if command -v netstat >/dev/null 2>&1; then
        if netstat -ln | grep ":$port " >/dev/null 2>&1; then
            echo_warn "⚠️  Port $port is already in use (required for $service_name)"
            echo_info "You may want to:"
            echo_info "  1. Stop the service using that port"
            echo_info "  2. Change the port in .env file"
            echo_info "  3. Use a different port: WORDPRESS_PORT=8081 $0"
            return 1
        fi
    fi
    return 0
}

show_service_info() {
    echo_info ""
    echo_info "🎉 WordPress environment is ready!"
    echo_info ""
    echo_info "📊 Service Information:"
    echo_info "  WordPress URL: http://localhost:${WORDPRESS_PORT:-8080}"
    echo_info "  Admin Panel:   http://localhost:${WORDPRESS_PORT:-8080}/wp-admin"
    echo_info "  MySQL Port:    ${MYSQL_PORT:-3306}"
    echo_info ""
    echo_info "🔐 Default Credentials:"
    echo_info "  Username: ${WP_ADMIN_USER:-admin}"
    echo_info "  Password: ${WP_ADMIN_PASSWORD:-admin123}"
    echo_info "  Email:    ${WP_ADMIN_EMAIL:-admin@testsite.com}"
    echo_info ""
    echo_info "👥 Test Users:"
    echo_info "  editor/password123     (Editor role)"
    echo_info "  subscriber/password123 (Subscriber role)"
    echo_info "  johndoe/password123    (Subscriber role)"
    echo_info ""
    echo_info "📝 Available Content:"
    echo_info "  • Posts and pages with PII patterns for testing"
    echo_info "  • User metadata with personal information"
    echo_info "  • Comments with contact details"
    echo_info "  • Various data types: emails, phones, SSNs, addresses"
    echo_info ""
    echo_info "🔧 Management Commands:"
    echo_info "  ./stop.sh              - Stop all containers"
    echo_info "  docker compose logs -f - View live logs"
    echo_info "  docker compose ps      - Check container status"
}

main() {
    echo_info "🚀 Starting Waivern WordPress Environment"
    echo_info "Working directory: $SCRIPT_DIR"

    # Load environment variables if .env exists
    if [ -f ".env" ]; then
        echo_info "Loading environment from .env file"
        set -a
        source .env
        set +a
    else
        echo_warn "No .env file found, using defaults"
    fi

    # Check if Docker is running
    echo_step "Checking Docker availability..."
    if ! docker info >/dev/null 2>&1; then
        echo_error "Docker is not running or not accessible"
        echo_info "Please start Docker and try again"
        exit 1
    fi

    # Check if required files exist
    local required_files=(
        "docker-compose.yml"
        "scripts/entrypoint.sh"
        "seed-data/01-seed-data.sql"
    )

    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo_error "Required file not found: $file"
            echo_info "Run ./build.sh first to set up the environment"
            exit 1
        fi
    done

    # Check port availability
    check_port_availability "${WORDPRESS_PORT:-8080}" "WordPress" || true
    check_port_availability "${MYSQL_PORT:-3306}" "MySQL" || true

    # Rebuild if requested
    if [ "${REBUILD:-false}" = true ]; then
        echo_step "Rebuilding containers..."
        docker compose build --no-cache
    fi

    # Stop any existing containers
    echo_step "Stopping any existing containers..."
    docker compose down 2>/dev/null || true

    # Start services
    echo_step "Starting WordPress and MySQL containers..."

    if [ "$DETACHED" = true ]; then
        docker compose up -d
    else
        echo_info "Starting in foreground mode (Ctrl+C to stop)..."
        docker compose up &
        COMPOSE_PID=$!
    fi

    # Wait for services to be ready
    if [ "$WAIT_FOR_READY" = true ]; then
        echo_step "Waiting for services to be ready..."

        # Wait for MySQL first
        echo_info "Waiting for MySQL to be healthy..."
        local mysql_ready=false
        for i in {1..30}; do
            if docker compose ps mysql | grep -q "healthy"; then
                mysql_ready=true
                break
            fi
            sleep 2
        done

        if [ "$mysql_ready" = false ]; then
            echo_error "MySQL failed to become healthy"
            docker compose logs mysql
            exit 1
        fi

        # Wait for WordPress
        if ! wait_for_service "WordPress" "http://localhost:${WORDPRESS_PORT:-8080}" 120; then
            echo_error "WordPress failed to start properly"
            echo_info "Container logs:"
            docker compose logs --tail=20
            exit 1
        fi

        # Give WordPress setup a moment to complete
        echo_info "Waiting for WordPress setup to complete..."
        sleep 10

        # Verify WordPress is properly installed
        local wp_ready=false
        for i in {1..20}; do
            if curl -f -s "http://localhost:${WORDPRESS_PORT:-8080}" | grep -q "Waivern\|WordPress" 2>/dev/null; then
                wp_ready=true
                break
            fi
            sleep 3
        done

        if [ "$wp_ready" = false ]; then
            echo_warn "WordPress may not be fully ready yet, but containers are running"
        fi
    fi

    # Show service information
    show_service_info

    # Show logs if requested
    if [ "$SHOW_LOGS" = true ]; then
        echo_step "Showing container logs (Ctrl+C to stop)..."
        docker compose logs -f
    fi

    # If running in foreground, wait for compose process
    if [ "$DETACHED" = false ] && [ -n "${COMPOSE_PID:-}" ]; then
        wait $COMPOSE_PID
    fi
}

# Handle Ctrl+C gracefully
trap 'echo_info "Shutting down..."; docker compose down; exit 0' INT

# Run main function
main "$@"
