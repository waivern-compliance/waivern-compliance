#!/bin/bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Function to wait for MySQL to be ready
wait_for_mysql() {
    echo_info "Waiting for MySQL to be ready..."
    echo_info "MySQL Host: ${WORDPRESS_DB_HOST:-not set}"
    echo_info "MySQL Database: ${WORDPRESS_DB_NAME:-not set}"
    echo_info "MySQL User: ${WORDPRESS_DB_USER:-not set}"

    # Validate required environment variables
    if [ -z "${WORDPRESS_DB_HOST:-}" ] || [ -z "${WORDPRESS_DB_NAME:-}" ] || [ -z "${WORDPRESS_DB_USER:-}" ] || [ -z "${WORDPRESS_DB_PASSWORD:-}" ]; then
        echo_error "Missing required MySQL environment variables"
        echo_error "Required: WORDPRESS_DB_HOST, WORDPRESS_DB_NAME, WORDPRESS_DB_USER, WORDPRESS_DB_PASSWORD"
        exit 1
    fi

    local max_attempts=60  # Increased from 30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        # Method 1: Try mysqladmin ping (most reliable)
        if command -v mysqladmin >/dev/null 2>&1; then
            if mysqladmin ping \
                --host="$WORDPRESS_DB_HOST" \
                --user="$WORDPRESS_DB_USER" \
                --password="$WORDPRESS_DB_PASSWORD" \
                --silent 2>/dev/null; then
                echo_info "MySQL is ready (verified with mysqladmin)!"
                return 0
            fi
        else
            # Method 2: Try mysql client connection
            if command -v mysql >/dev/null 2>&1; then
                if mysql \
                    --host="$WORDPRESS_DB_HOST" \
                    --user="$WORDPRESS_DB_USER" \
                    --password="$WORDPRESS_DB_PASSWORD" \
                    --execute="SELECT 1;" >/dev/null 2>&1; then
                    echo_info "MySQL is ready (verified with mysql client)!"
                    return 0
                fi
            else
                # Method 3: Fallback to TCP connection test with better error handling
                if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$WORDPRESS_DB_HOST/3306" 2>/dev/null; then
                    echo_info "MySQL TCP connection successful!"
                    # Additional wait to ensure MySQL is fully ready
                    sleep 3
                    return 0
                fi
            fi
        fi

        if [ $((attempt % 10)) -eq 0 ]; then
            echo_warn "Still waiting for MySQL... (attempt $attempt/$max_attempts)"
            echo_info "Trying to resolve: $WORDPRESS_DB_HOST"
            nslookup "$WORDPRESS_DB_HOST" 2>/dev/null || echo_warn "DNS resolution failed"
        fi

        sleep 2
        ((attempt++))
    done

    echo_error "MySQL failed to become ready after $max_attempts attempts"
    echo_error "Debug information:"
    echo_error "  Host: $WORDPRESS_DB_HOST"
    echo_error "  Port: 3306"
    echo_error "  User: $WORDPRESS_DB_USER"
    echo_error "  Database: $WORDPRESS_DB_NAME"

    # Try one final connection test with verbose output
    echo_info "Final connection test:"
    timeout 5 bash -c "cat < /dev/null > /dev/tcp/$WORDPRESS_DB_HOST/3306" || echo_error "TCP connection failed"

    exit 1
}

# Function to install WordPress if not already installed
install_wordpress() {
    # First, download WordPress core files if they don't exist
    if [ ! -f "/var/www/html/wp-config-sample.php" ]; then
        echo_info "Downloading WordPress core files..."
        wp --allow-root core download --skip-content
        echo_info "WordPress core files downloaded successfully"
    else
        echo_info "WordPress core files already exist"
    fi

    # Create wp-config.php if it doesn't exist
    if [ ! -f "/var/www/html/wp-config.php" ]; then
        echo_info "Creating wp-config.php..."
        wp --allow-root config create \
            --dbname="$WORDPRESS_DB_NAME" \
            --dbuser="$WORDPRESS_DB_USER" \
            --dbpass="$WORDPRESS_DB_PASSWORD" \
            --dbhost="$WORDPRESS_DB_HOST" \
            --skip-check
        echo_info "wp-config.php created successfully"
    else
        echo_info "wp-config.php already exists"
    fi

    if ! wp --allow-root core is-installed 2>/dev/null; then
        echo_info "Installing WordPress..."

        wp --allow-root core install \
            --url="${WP_URL:-http://localhost:8080}" \
            --title="${WP_TITLE:-Waivern Test Site}" \
            --admin_user="${WP_ADMIN_USER:-admin}" \
            --admin_password="${WP_ADMIN_PASSWORD:-admin123}" \
            --admin_email="${WP_ADMIN_EMAIL:-admin@testsite.com}" \
            --skip-email

        echo_info "WordPress installed successfully"
    else
        echo_info "WordPress is already installed"
    fi
}

# Function to install and activate plugins
install_plugins() {
    echo_info "Installing and activating plugins..."

    # Install common plugins that might be useful for testing
    local plugins=(
        "contact-form-7"
        "woocommerce"
        "user-registration"
    )

    for plugin in "${plugins[@]}"; do
        if ! wp --allow-root plugin is-installed "$plugin" 2>/dev/null; then
            echo_info "Installing plugin: $plugin"
            wp --allow-root plugin install "$plugin" --activate || echo_warn "Failed to install $plugin"
        else
            echo_info "Plugin $plugin is already installed"
            wp --allow-root plugin activate "$plugin" 2>/dev/null || echo_warn "Failed to activate $plugin"
        fi
    done

    # Install any custom plugins from the plugins directory
    if [ -d "/tmp/plugins" ] && [ "$(ls -A /tmp/plugins)" ]; then
        echo_info "Installing custom plugins from /tmp/plugins..."
        for plugin_file in /tmp/plugins/*.zip; do
            if [ -f "$plugin_file" ]; then
                echo_info "Installing custom plugin: $(basename "$plugin_file")"
                wp --allow-root plugin install "$plugin_file" --activate || echo_warn "Failed to install $(basename "$plugin_file")"
            fi
        done
    fi
}

# Function to setup permalinks and other configurations
configure_wordpress() {
    echo_info "Configuring WordPress settings..."

    # Set pretty permalinks
    wp --allow-root rewrite structure '/%postname%/' --hard

    # Update site URLs to match the environment
    wp --allow-root option update home "${WP_URL:-http://localhost:8080}"
    wp --allow-root option update siteurl "${WP_URL:-http://localhost:8080}"

    # Enable debug logging
    wp --allow-root config set WP_DEBUG true --raw
    wp --allow-root config set WP_DEBUG_LOG true --raw
    wp --allow-root config set WP_DEBUG_DISPLAY false --raw

    echo_info "WordPress configuration complete"
}

# Function to create additional test users
create_test_users() {
    echo_info "Creating additional test users..."

    # Create users if they don't exist
    local users=(
        "editor:editor@testsite.com:editor:Content Editor"
        "subscriber:subscriber@testsite.com:subscriber:John Subscriber"
        "johndoe:john.doe@example.com:subscriber:John Doe"
    )

    for user_info in "${users[@]}"; do
        IFS=':' read -r username email role display_name <<< "$user_info"

        if ! wp --allow-root user get "$username" 2>/dev/null; then
            echo_info "Creating user: $username"
            wp --allow-root user create "$username" "$email" \
                --role="$role" \
                --display_name="$display_name" \
                --user_pass="password123" \
                --send-email=false
        else
            echo_info "User $username already exists"
        fi
    done
}

# Function to import demo content
import_demo_content() {
    echo_info "Checking if demo content needs to be imported..."

    # Check if we already have demo posts
    local post_count=$(wp --allow-root post list --post_type=post --format=count)

    if [ "$post_count" -eq 0 ] || [ "${FORCE_IMPORT:-false}" = "true" ]; then
        echo_info "Importing demo content with PII patterns..."

        # Import test posts with PII content
        wp --allow-root post create --post_title="Welcome Post" \
            --post_content="Welcome to our website! For support, please contact us at support@testsite.com or call us at +1 (555) 123-4567. Our office is located at 456 Business Ave, Suite 100, Business City, BC 54321." \
            --post_status=publish \
            --post_author=1

        wp --allow-root post create --post_title="Customer Testimonial" \
            --post_content="Customer testimonial: \"I had an issue with my order and contacted customer service. Sarah Johnson (sarah.johnson@company.com) was incredibly helpful. You can reach her at extension 1234 or her direct line (555) 987-6543. My account number is ACC-789012 for reference.\" - Customer ID: CUST-456789" \
            --post_status=publish \
            --post_author=2

        wp --allow-root post create --post_title="Privacy Policy" \
            --post_content="Privacy Policy: We collect personal information including names, email addresses, phone numbers, and billing addresses. For EU residents, your GDPR rights include data portability. Contact our Data Protection Officer at dpo@testsite.com. For California residents under CCPA, you may request deletion of personal data by emailing privacy@testsite.com or calling 1-800-PRIVACY." \
            --post_status=publish \
            --post_type=page \
            --post_author=1

        echo_info "Demo content imported successfully"
    else
        echo_info "Demo content already exists (found $post_count posts)"
    fi
}

# Main execution
main() {
    echo_info "Starting Waivern WordPress setup..."
    echo_info "WordPress DB Host: ${WORDPRESS_DB_HOST:-not set}"
    echo_info "WordPress URL: ${WP_URL:-http://localhost:8080}"

    # Wait for MySQL to be ready
    wait_for_mysql

    # Start the original WordPress entrypoint in the background
    echo_info "Starting WordPress Apache server..."
    apache2-foreground &

    # Wait a moment for Apache to start
    sleep 5

    # Download and install WP-CLI if not present
    if ! command -v wp &> /dev/null; then
        echo_info "Installing WP-CLI..."
        curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar
        chmod +x wp-cli.phar
        mv wp-cli.phar /usr/local/bin/wp
    fi

    # Wait for WordPress to be accessible
    echo_info "Waiting for WordPress to be accessible..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost/wp-admin/install.php >/dev/null 2>&1; then
            echo_info "WordPress is accessible!"
            break
        fi

        echo_warn "WordPress not accessible yet. Attempt $attempt/$max_attempts. Waiting 2 seconds..."
        sleep 2
        ((attempt++))

        if [ $attempt -gt $max_attempts ]; then
            echo_error "WordPress failed to become accessible"
            exit 1
        fi
    done

    # Change to WordPress directory
    cd /var/www/html

    # Install WordPress
    install_wordpress

    # Configure WordPress
    configure_wordpress

    # Create test users
    create_test_users

    # Install and activate plugins
    install_plugins

    # Import demo content
    import_demo_content

    echo_info "WordPress setup complete!"
    echo_info "Access your WordPress site at: ${WP_URL:-http://localhost:8080}"
    echo_info "Admin credentials: ${WP_ADMIN_USER:-admin} / ${WP_ADMIN_PASSWORD:-admin123}"

    # Keep the container running
    wait
}

# Run main function
main
