#!/bin/bash

# Hetzner VM Setup Script for Corpus TE
# Run this script on a fresh Ubuntu/Debian server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${YELLOW}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

echo -e "${GREEN}Setting up Hetzner VM for Corpus TE...${NC}"

# Update system
print_step "Updating system packages..."
sudo apt update && sudo apt upgrade -y
print_success "System updated"

# Install essential packages
print_step "Installing essential packages..."
sudo apt install -y \
    curl \
    wget \
    git \
    htop \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban \
    logrotate
print_success "Essential packages installed"

# Install Docker
if ! command -v docker &> /dev/null; then
    print_step "Installing Docker..."
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    print_success "Docker installed"
else
    print_success "Docker already installed"
fi

# Configure firewall
print_step "Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (adjust port if needed)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application port
sudo ufw allow 8000/tcp

# Allow Flower (Celery monitoring) - restrict to specific IPs in production
sudo ufw allow 5555/tcp

# Enable firewall
sudo ufw --force enable
print_success "Firewall configured"

# Configure fail2ban
print_step "Configuring fail2ban..."
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Create custom jail for SSH
sudo tee /etc/fail2ban/jail.d/ssh.conf > /dev/null <<EOF
[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
findtime = 600
EOF

sudo systemctl enable fail2ban
sudo systemctl restart fail2ban
print_success "Fail2ban configured"

# Create project directories
print_step "Creating project directories..."
sudo mkdir -p /opt/corpus-te
sudo mkdir -p /opt/corpus-te/backups
sudo mkdir -p /opt/corpus-te/logs
sudo chown -R $USER:$USER /opt/corpus-te
print_success "Project directories created"

# Install Nginx (optional, for reverse proxy)
if ! command -v nginx &> /dev/null; then
    print_step "Installing Nginx..."
    sudo apt install -y nginx
    sudo systemctl enable nginx
    print_success "Nginx installed"
fi

# Create Nginx configuration for reverse proxy
print_step "Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/corpus-te > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /flower/ {
        proxy_pass http://localhost:5555/flower/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        auth_basic "Flower";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
}
EOF

# Enable the site
sudo ln -sf /etc/nginx/sites-available/corpus-te /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t
sudo systemctl reload nginx
print_success "Nginx configured"

# Setup log rotation
print_step "Setting up log rotation..."
sudo tee /etc/logrotate.d/corpus-te > /dev/null <<EOF
/opt/corpus-te/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        docker compose -f /opt/corpus-te/docker-compose.prod.yml restart app > /dev/null 2>&1 || true
    endscript
}
EOF
print_success "Log rotation configured"

# Create backup script
print_step "Creating backup script..."
sudo tee /opt/corpus-te/backup.sh > /dev/null <<'EOF'
#!/bin/bash

# Corpus TE Backup Script
BACKUP_DIR="/opt/corpus-te/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.sql"
RETENTION_DAYS=7

# Create database backup
docker compose -f /opt/corpus-te/docker-compose.prod.yml exec -T postgres pg_dump -U postgres corpus_te > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove old backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: ${BACKUP_FILE}.gz"
EOF

chmod +x /opt/corpus-te/backup.sh
print_success "Backup script created"

# Setup cron job for daily backups
print_step "Setting up daily backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/corpus-te/backup.sh") | crontab -
print_success "Daily backup cron job created"

# Create monitoring script
print_step "Creating monitoring script..."
sudo tee /opt/corpus-te/monitor.sh > /dev/null <<'EOF'
#!/bin/bash

# Simple monitoring script for Corpus TE
cd /opt/corpus-te

# Check if services are running
if ! docker compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    echo "$(date): Some services are down" >> logs/monitor.log
    # Restart services
    docker compose -f docker-compose.prod.yml up -d
fi

# Check disk usage
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "$(date): Disk usage is high: ${DISK_USAGE}%" >> logs/monitor.log
fi

# Check application health
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "$(date): Application health check failed" >> logs/monitor.log
fi
EOF

chmod +x /opt/corpus-te/monitor.sh

# Setup monitoring cron job (every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/corpus-te/monitor.sh") | crontab -
print_success "Monitoring script and cron job created"

echo -e "${GREEN}"
echo "=============================================="
echo "  Hetzner VM Setup Complete!"
echo "=============================================="
echo "Next steps:"
echo "1. Reboot the server: sudo reboot"
echo "2. After reboot, upload your application code"
echo "3. Create .env file from .env.example"
echo "4. Run the deployment script: ./deploy.sh"
echo "5. Update Nginx server_name with your domain"
echo "6. Setup SSL with Let's Encrypt (optional)"
echo -e "${NC}"

print_step "Setup completed! Please reboot the server before deploying the application."
