# Waivern WordPress Test Environment

A fully containerized WordPress test environment with realistic seed data containing PII patterns for testing the Waivern WordPress plugin.

## 🚀 Quick Start

```bash
# 1. Build the environment
./build.sh

# 2. Start WordPress
./start.sh

# 3. Access WordPress
open http://localhost:8080
```

**Default Credentials:**

- **Username:** `admin`
- **Password:** `admin123`
- **Email:** `admin@testsite.com`

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Test Data](#test-data)
- [Development](#development)
- [CI Integration](#ci-integration)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Prerequisites

- **Docker** (20.10.0 or later)
- **Docker Compose** (2.0.0 or later)
- **curl** (for health checks)
- **bash** (4.0 or later)

### System Requirements

- **RAM:** 2GB minimum, 4GB recommended
- **Storage:** 5GB free space
- **Ports:** 8080 (WordPress), 3306 (MySQL)

### Docker Configuration

⚠️ **Important**: This environment requires **root Docker context** for proper container management.

```bash
# Check your current Docker context
docker context ls

# Switch to default (root) context if needed
docker context use default

# Ensure system Docker daemon is running
sudo systemctl start docker
```

**Note**: Docker Rootless mode has limitations with container process management that can cause permission denied errors when stopping containers.

## Installation

### 1. Clone and Setup

```bash
git clone <repository-url>
cd analyser/docker/wordpress
```

### 2. Build Environment

```bash
# Standard build
./build.sh

# Clean build (removes existing data)
./build.sh --clean

# Pull images only
./build.sh --pull-only
```

### 3. Start Services

```bash
# Start in background
./start.sh

# Start in foreground with logs
./start.sh --foreground --logs

# Start with rebuild
./start.sh --rebuild
```

## Usage

### Management Commands

| Command      | Description                | Options                                 |
| ------------ | -------------------------- | --------------------------------------- |
| `./build.sh` | Build/setup environment    | `--clean`, `--no-pull`, `--pull-only`   |
| `./start.sh` | Start WordPress containers | `--foreground`, `--logs`, `--rebuild`   |
| `./stop.sh`  | Stop containers            | `--volumes`, `--images`, `--full-clean` |

### Common Workflows

#### Local Development

```bash
# Initial setup
./build.sh
./start.sh

# Daily development
./start.sh  # Start when needed
./stop.sh   # Stop when done

# Reset environment
./stop.sh --volumes  # Remove all data
./start.sh          # Fresh start with seed data
```

#### Testing WordPress Plugin

```bash
# Start test environment
./start.sh

# Run your plugin tests against http://localhost:8080
python -m pytest tests/

# Stop when done
./stop.sh
```

#### CI/CD Pipeline

```bash
# In CI environment with random ports
WORDPRESS_PORT=0 MYSQL_PORT=0 ./start.sh --no-wait
# Run integration tests
./stop.sh --full-clean
```

## Configuration

### Environment Variables

Create a `.env` file to customize configuration:

```bash
# Port Configuration
WORDPRESS_PORT=8080
MYSQL_PORT=3306

# WordPress Configuration
WP_URL=http://localhost:8080
WP_TITLE=Waivern Test Site
WP_ADMIN_USER=admin
WP_ADMIN_PASSWORD=admin123
WP_ADMIN_EMAIL=admin@testsite.com

# Import Configuration
FORCE_IMPORT=false

# Build Configuration
PULL_IMAGES=true
CLEAN_BUILD=false
```

⚠️ **Note**: If you don't have a `.env` file, the start script will create one automatically with default ports.

### Port Configuration

To avoid conflicts, especially in CI:

```bash
# Create .env file with specific ports
echo "WORDPRESS_PORT=8080" > .env
echo "MYSQL_PORT=3306" >> .env

# Use environment variables for one-time override
WORDPRESS_PORT=8081 MYSQL_PORT=3307 ./start.sh

# Use random available ports (CI environments)
WORDPRESS_PORT=0 MYSQL_PORT=0 ./start.sh

# Check what ports were assigned
docker compose ps
```

**Common Port Conflicts:**

- Port 3306: Default MySQL port (may conflict with local MySQL)
- Port 8080: Common development port (may conflict with other apps)

**Solutions:**

- Use alternative ports: `MYSQL_PORT=3307 WORDPRESS_PORT=8081`
- Stop conflicting services: `sudo systemctl stop mysql`
- Use Docker context isolation (see Prerequisites)

### Custom Plugins

Place plugin `.zip` files in the `plugins/` directory:

```bash
# Add custom plugins
cp your-plugin.zip docker/wordpress/plugins/

# Restart to install
./stop.sh && ./start.sh
```

## Test Data

The environment includes comprehensive test data with various PII patterns:

### Users

- **admin** (Administrator) - Full admin access
- **editor** (Editor) - Content management
- **subscriber** (Subscriber) - Basic user
- **johndoe** (Subscriber) - User with PII data

### Content Types

- **Posts:** Blog posts with embedded PII
- **Pages:** Privacy policies, contact forms
- **Comments:** Customer feedback with contact info
- **Metadata:** Custom fields with personal data

### PII Patterns Included

- **Email addresses:** Various formats and domains
- **Phone numbers:** US, UK, international formats
- **Addresses:** Street addresses, business locations
- **SSNs:** Social Security Numbers (fake)
- **Account numbers:** Customer IDs, account references
- **Names:** Full names, partial names
- **Dates of birth:** Various date formats

### Accessing Test Data

```bash
# View database directly
docker compose exec mysql mysql -u wordpress -pwordpress wordpress

# Use WP-CLI
docker compose exec wordpress wp --allow-root post list

# Export current data
docker compose exec mysql mysqldump -u wordpress -pwordpress wordpress > backup.sql
```

## Development

### WordPress Development

```bash
# Access WordPress container
docker compose exec wordpress bash

# Use WP-CLI commands
docker compose exec wordpress wp --allow-root plugin list
docker compose exec wordpress wp --allow-root user list

# View logs
docker compose logs -f wordpress
```

### Database Operations

```bash
# Access MySQL
docker compose exec mysql mysql -u wordpress -pwordpress

# View tables
docker compose exec mysql mysql -u wordpress -pwordpress -e "SHOW TABLES;" wordpress

# Backup database
docker compose exec mysql mysqldump -u wordpress -pwordpress wordpress > backup.sql

# Restore database
docker compose exec -T mysql mysql -u wordpress -pwordpress wordpress < backup.sql
```

### File System Access

```bash
# WordPress files
docker compose exec wordpress ls -la /var/www/html/

# Upload files
docker cp local-file.txt waivern_wordpress:/var/www/html/

# Download files
docker cp waivern_wordpress:/var/www/html/wp-config.php ./
```

## CI Integration

### GitHub Actions

The environment is designed for CI/CD integration. Example workflow:

```yaml
name: WordPress Plugin Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup WordPress Test Environment
        run: |
          cd docker/wordpress
          ./build.sh --no-pull
          WORDPRESS_PORT=0 MYSQL_PORT=0 ./start.sh

      - name: Run Plugin Tests
        run: |
          # Your plugin tests here
          python -m pytest tests/

      - name: Cleanup
        if: always()
        run: |
          cd docker/wordpress
          ./stop.sh --full-clean
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Setup') {
            steps {
                dir('docker/wordpress') {
                    sh './build.sh'
                    sh 'WORDPRESS_PORT=0 MYSQL_PORT=0 ./start.sh'
                }
            }
        }
        stage('Test') {
            steps {
                sh 'python -m pytest tests/'
            }
        }
    }
    post {
        always {
            dir('docker/wordpress') {
                sh './stop.sh --full-clean'
            }
        }
    }
}
```

### Docker Compose for CI

For CI environments, use random ports:

```bash
# Generate random ports
export WORDPRESS_PORT=$(shuf -i 8000-8999 -n 1)
export MYSQL_PORT=$(shuf -i 3400-3499 -n 1)

# Start with generated ports
./start.sh
```

## Troubleshooting

### Common Issues

#### Port Conflicts

```bash
# Error: Port 8080 already in use
# Solution 1: Use different port
WORDPRESS_PORT=8081 ./start.sh

# Solution 2: Create .env file with different ports
echo "WORDPRESS_PORT=8081" > .env
echo "MYSQL_PORT=3307" >> .env
./start.sh

# Solution 3: Stop conflicting service
sudo lsof -i :8080
kill <PID>
```

#### Docker Context Issues

**Problem**: Containers won't stop, "permission denied" errors
**Cause**: Running in Docker Rootless mode

```bash
# Check current context
docker context ls

# Switch to root context
docker context use default
sudo systemctl start docker

# Clean up and restart
./stop.sh
./start.sh
```

**Problem**: Command not found or daemon connection errors
**Cause**: Wrong Docker context or daemon not running

```bash
# Check Docker status
systemctl --user status docker  # For rootless
sudo systemctl status docker    # For root

# Switch context and restart daemon
docker context use default
sudo systemctl restart docker
```

#### MySQL Connection Issues

```bash
# Check MySQL health
docker compose ps mysql

# View MySQL logs
docker compose logs mysql

# Reset MySQL
./stop.sh --volumes && ./start.sh

# Test MySQL connectivity
docker compose exec mysql mysqladmin -u wordpress -pwordpress ping
```

#### WordPress Not Loading

```bash
# Check container status
docker compose ps

# View WordPress logs
docker compose logs wordpress

# Check health endpoint
curl -I http://localhost:8080/wp-admin/install.php

# Check if WordPress is accessible
curl -f http://localhost:8080 || echo "WordPress not accessible"
```

#### Permission Issues

**Script Permission Issues:**

```bash
# Fix script permissions
chmod +x *.sh
```

**WordPress File Permission Issues:**

```bash
# Fix WordPress permissions
docker compose exec wordpress chown -R www-data:www-data /var/www/html
```

**Container Stop Permission Denied:**
This is usually caused by Docker Rootless mode limitations.

```bash
# Check current Docker context
docker context ls

# Switch to root Docker context
docker context use default

# Ensure system Docker daemon is running
sudo systemctl start docker

# Try stopping again
docker compose down
```

**If containers are stuck in rootless context:**

```bash
# Switch to rootless context to clean up
docker context use rootless

# Force remove stuck containers
docker rm -f waivern_mysql waivern_wordpress 2>/dev/null || true
docker system prune -f

# Switch back to default context
docker context use default

# Restart environment
./start.sh
```

**Error: "cannot stop container: permission denied"**

- **Cause**: Docker Rootless mode process signaling limitations
- **Solution**: Use default Docker context (see above)
- **Prevention**: Always use `docker context use default` before starting

### Debug Mode

Enable debug logging:

```bash
# Set debug environment
echo "WORDPRESS_DEBUG=1" >> .env
echo "WP_DEBUG_LOG=true" >> .env

# Restart containers
./stop.sh && ./start.sh

# View debug logs
docker compose exec wordpress tail -f /var/www/html/wp-content/debug.log
```

### Health Checks

```bash
# Check all services
docker compose ps

# Test WordPress availability
curl -f http://localhost:8080

# Test MySQL connectivity
docker compose exec mysql mysqladmin -u wordpress -pwordpress ping

# Comprehensive health check
./start.sh --logs  # Watch startup logs

# Check Docker context and daemon status
docker context ls
docker info | head -10
```

## Maintenance

### Updating WordPress Version

1. Update version in `docker-compose.yml`:

```yaml
wordpress:
  image: wordpress:6.5-php8.2-apache # Update version
```

2. Rebuild environment:

```bash
./build.sh --clean
./start.sh
```

### Updating Seed Data

1. Modify `seed-data/01-seed-data.sql`
2. Force reimport:

```bash
echo "FORCE_IMPORT=true" >> .env
./stop.sh --volumes
./start.sh
```

3. Reset environment variable:

```bash
sed -i 's/FORCE_IMPORT=true/FORCE_IMPORT=false/' .env
```

### Backup and Restore

#### Backup

```bash
# Backup database
docker compose exec mysql mysqldump -u wordpress -pwordpress wordpress > backup-$(date +%Y%m%d).sql

# Backup WordPress files
docker compose exec wordpress tar -czf - /var/www/html | cat > wordpress-backup-$(date +%Y%m%d).tar.gz
```

#### Restore

```bash
# Restore database
docker compose exec -T mysql mysql -u wordpress -pwordpress wordpress < backup-20240101.sql

# Restore WordPress files
docker compose exec -T wordpress tar -xzf - -C / < wordpress-backup-20240101.tar.gz
```

### Version Management

Track seed data versions:

```bash
# Version your seed data
cp seed-data/01-seed-data.sql seed-data/v1.0-seed-data.sql

# Document changes
echo "v1.0 - Initial PII test data with users, posts, comments" >> seed-data/CHANGELOG.md
```

### Performance Optimization

For better performance:

```bash
# Use specific MySQL version
# In docker-compose.yml, pin to specific tag
mysql:
  image: mysql:8.0.35  # Instead of mysql:8.0

# Increase memory limits
# Add to docker-compose.yml
services:
  mysql:
    deploy:
      resources:
        limits:
          memory: 1G
```

## Security Notes

⚠️ **This is a test environment only!**

- Uses default passwords (`admin123`)
- Contains fake PII data for testing
- Not suitable for production use
- All data is for testing purposes only

## License

This test environment is part of the Waivern project. See the main project license for details.

## Support

For issues and questions:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review container logs: `docker compose logs`
3. Open an issue in the main project repository
4. Check Docker and system requirements

---

**Happy Testing! 🎉**
