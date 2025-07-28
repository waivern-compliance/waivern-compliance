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
REMOVE_VOLUMES=${REMOVE_VOLUMES:-false}
REMOVE_IMAGES=${REMOVE_IMAGES:-false}
FORCE_REMOVE=${FORCE_REMOVE:-false}
CLEANUP_SYSTEM=${CLEANUP_SYSTEM:-false}

show_help() {
    cat << EOF
Waivern WordPress Docker Stop Script

Usage: $0 [OPTIONS]

Options:
    -h, --help          Show this help message
    -v, --volumes       Remove volumes (deletes all data)
    -i, --images        Remove WordPress and MySQL images
    -f, --force         Force removal without confirmation
    -c, --cleanup       Clean up unused Docker resources
    --full-clean        Remove everything (containers, volumes, images, networks)

Environment Variables:
    REMOVE_VOLUMES      Remove volumes on stop (default: false)
    REMOVE_IMAGES       Remove images on stop (default: false)
    FORCE_REMOVE        Skip confirmation prompts (default: false)

Examples:
    $0                  # Stop containers only
    $0 --volumes        # Stop and remove volumes (data loss!)
    $0 --full-clean     # Complete cleanup
    $0 -f --volumes     # Force stop with volume removal
    
⚠️  WARNING: Using --volumes will delete all WordPress data permanently!
    
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        -i|--images)
            REMOVE_IMAGES=true
            shift
            ;;
        -f|--force)
            FORCE_REMOVE=true
            shift
            ;;
        -c|--cleanup)
            CLEANUP_SYSTEM=true
            shift
            ;;
        --full-clean)
            REMOVE_VOLUMES=true
            REMOVE_IMAGES=true
            CLEANUP_SYSTEM=true
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

confirm_action() {
    local message=$1
    
    if [ "$FORCE_REMOVE" = true ]; then
        return 0
    fi
    
    echo_warn "$message"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo_info "Cancelled."
        return 1
    fi
    return 0
}

show_containers_status() {
    echo_step "Current container status:"
    docker compose ps 2>/dev/null || echo_info "No containers found"
}

stop_containers() {
    echo_step "Stopping WordPress containers..."
    
    if docker compose ps | grep -q "Up"; then
        echo_info "Stopping running containers..."
        docker compose stop
        echo_info "✅ Containers stopped"
    else
        echo_info "No running containers found"
    fi
    
    echo_info "Removing containers..."
    docker compose down --remove-orphans
    echo_info "✅ Containers removed"
}

remove_volumes() {
    if [ "$REMOVE_VOLUMES" = true ]; then
        echo_step "Removing volumes..."
        
        if ! confirm_action "⚠️  This will PERMANENTLY DELETE all WordPress data including posts, users, and uploads!"; then
            return
        fi
        
        echo_info "Stopping containers with volume removal..."
        docker compose down --volumes --remove-orphans
        
        # Remove named volumes specifically
        local volumes=(
            "wordpress_mysql_data"
            "wordpress_wordpress_data"
        )
        
        for volume in "${volumes[@]}"; do
            if docker volume ls | grep -q "$volume"; then
                echo_info "Removing volume: $volume"
                docker volume rm "$volume" 2>/dev/null || echo_warn "Could not remove volume: $volume"
            fi
        done
        
        echo_info "✅ Volumes removed"
    fi
}

remove_images() {
    if [ "$REMOVE_IMAGES" = true ]; then
        echo_step "Removing Docker images..."
        
        if ! confirm_action "This will remove WordPress and MySQL images (they can be re-downloaded)."; then
            return
        fi
        
        local images=(
            "wordpress:6.4-php8.2-apache"
            "mysql:8.0"
        )
        
        for image in "${images[@]}"; do
            if docker images | grep -q "$image"; then
                echo_info "Removing image: $image"
                docker image rm "$image" 2>/dev/null || echo_warn "Could not remove image: $image"
            else
                echo_info "Image not found: $image"
            fi
        done
        
        echo_info "✅ Images removed"
    fi
}

cleanup_system() {
    if [ "$CLEANUP_SYSTEM" = true ]; then
        echo_step "Cleaning up Docker system..."
        
        echo_info "Removing unused networks..."
        docker network prune -f
        
        echo_info "Removing unused volumes..."
        docker volume prune -f
        
        echo_info "Removing unused images..."
        docker image prune -f
        
        echo_info "✅ System cleanup complete"
    fi
}

show_cleanup_summary() {
    echo_step "Cleanup Summary:"
    
    local actions=()
    
    if docker compose ps 2>/dev/null | grep -q "waivern"; then
        actions+=("❌ Containers: Still running")
    else
        actions+=("✅ Containers: Stopped and removed")
    fi
    
    if [ "$REMOVE_VOLUMES" = true ]; then
        if docker volume ls | grep -q "wordpress_"; then
            actions+=("❌ Volumes: Some may still exist")
        else
            actions+=("✅ Volumes: Removed")
        fi
    else
        actions+=("ℹ️  Volumes: Preserved (use --volumes to remove)")
    fi
    
    if [ "$REMOVE_IMAGES" = true ]; then
        actions+=("✅ Images: Removed")
    else
        actions+=("ℹ️  Images: Preserved (use --images to remove)")
    fi
    
    for action in "${actions[@]}"; do
        echo_info "$action"
    done
    
    echo_info ""
    echo_info "🔧 Available commands:"
    echo_info "  ./start.sh             - Start WordPress environment"
    echo_info "  ./build.sh             - Rebuild environment"
    echo_info "  ./stop.sh --full-clean - Complete cleanup"
}

main() {
    echo_info "🛑 Stopping Waivern WordPress Environment"
    echo_info "Working directory: $SCRIPT_DIR"
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        echo_error "Docker is not running or not accessible"
        exit 1
    fi
    
    # Show current status
    show_containers_status
    
    # Stop containers
    stop_containers
    
    # Remove volumes if requested
    remove_volumes
    
    # Remove images if requested
    remove_images
    
    # Cleanup system if requested
    cleanup_system
    
    # Show summary
    show_cleanup_summary
    
    echo_info ""
    echo_info "🎯 WordPress environment stopped successfully!"
    
    if [ "$REMOVE_VOLUMES" = true ]; then
        echo_warn "⚠️  All data has been permanently deleted!"
        echo_info "Run ./start.sh to create a fresh environment with seed data."
    else
        echo_info "Data has been preserved. Run ./start.sh to restart with existing data."
    fi
}

# Run main function
main "$@" 