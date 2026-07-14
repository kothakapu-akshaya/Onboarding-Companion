# Hetzner VM Deployment Guide for Corpus TE

This guide will help you deploy the Corpus TE application to a Hetzner Cloud VPS.

## Prerequisites

- A Hetzner Cloud VPS (Ubuntu 20.04+ or Debian 11+ recommended)
- SSH access to your server
- Domain name (optional, for SSL setup)

## Server Specifications

### Minimum Requirements
- **CPU**: 2 vCPUs
- **RAM**: 4 GB
- **Storage**: 40 GB SSD
- **Network**: Good network connectivity

### Recommended for Production
- **CPU**: 4 vCPUs
- **RAM**: 8 GB
- **Storage**: 80 GB SSD
- **Backup**: Enable automated backups

## Step 1: Server Setup

1. **Connect to your server**:
   ```bash
   ssh root@your-server-ip
   ```

2. **Create a non-root user** (if not already done):
   ```bash
   adduser deploy
   usermod -aG sudo deploy
   su - deploy
   ```

3. **Copy the server setup script to your server**:
   ```bash
   # On your local machine
   scp setup-server.sh deploy@your-server-ip:~/
   
   # On the server
   chmod +x setup-server.sh
   ./setup-server.sh
   ```

4. **Reboot the server**:
   ```bash
   sudo reboot
   ```

## Step 2: Application Deployment

1. **Build and save the Docker image locally**:
   ```bash
   # On your local machine
   cd /path/to/corpus-te
   docker build -t corpus-te-app .
   docker save corpus-te-app > corpus-te-app.tar
   ```

2. **Transfer files to the server**:
   ```bash
   # Create deployment package
   tar -czf corpus-te-deploy.tar.gz \
     docker-compose.yml \
     docker-compose.prod.yml \
     .env.example \
     deploy.sh \
     corpus-te-app.tar

   # Upload to server
   scp corpus-te-deploy.tar.gz deploy@your-server-ip:~/
   ```

3. **Extract and deploy on the server**:
   ```bash
   # On the server
   cd ~
   tar -xzf corpus-te-deploy.tar.gz
   
   # Load Docker image
   docker load < corpus-te-app.tar
   
   # Create environment file
   cp .env.example .env
   nano .env  # Edit with your configuration
   ```

4. **Configure environment variables**:
   ```bash
   # Edit .env file with your settings
   POSTGRES_PASSWORD=your_secure_database_password
   SECRET_KEY=your_very_long_and_random_secret_key
   FLOWER_PASSWORD=your_flower_monitoring_password
   ```

5. **Run the deployment**:
   ```bash
   ./deploy.sh
   ```

## Step 3: SSL Setup (Optional but Recommended)

1. **Install Certbot**:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Update Nginx configuration**:
   ```bash
   sudo nano /etc/nginx/sites-available/corpus-te
   # Replace 'your-domain.com' with your actual domain
   ```

3. **Obtain SSL certificate**:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

## Step 4: Monitoring and Maintenance

### Application URLs
- **Main Application**: `http://your-server-ip:8000` or `https://your-domain.com`
- **Celery Monitoring (Flower)**: `http://your-server-ip:5555/flower`
- **Database**: PostgreSQL on port 5432 (internal only)

### Useful Commands

**View application logs**:
```bash
cd /opt/corpus-te
docker compose --profile production logs -f app
```

**View all service logs**:
```bash
docker compose --profile production logs -f
```

**Restart services**:
```bash
docker compose --profile production restart
```

**Update application**:
```bash
# Build new image locally and transfer
# Then run:
docker compose --profile production down
docker load < new-corpus-te-app.tar
docker compose --profile production up -d
```

**Database backup**:
```bash
# Manual backup
/opt/corpus-te/backup.sh

# Restore from backup
gunzip backup_YYYYMMDD_HHMMSS.sql.gz
docker compose --profile production exec -T postgres psql -U postgres -d corpus_te < backup_YYYYMMDD_HHMMSS.sql
```

### Monitoring

The system includes automatic monitoring:
- **Health checks**: Every 5 minutes
- **Daily backups**: At 2:00 AM
- **Log rotation**: Daily with 52-day retention
- **Service auto-restart**: If containers go down

### Security Features

- **Firewall**: UFW configured with minimal open ports
- **Fail2ban**: Protection against brute force attacks
- **Non-root containers**: All application containers run as non-root user
- **Network isolation**: Services run in isolated Docker network
- **Basic auth**: Flower monitoring protected with authentication

## Troubleshooting

### Common Issues

1. **Services won't start**:
   - Check logs: `docker compose --profile production logs`
   - Verify environment variables in `.env`
   - Ensure database password is correct

2. **Database connection issues**:
   - Verify PostgreSQL is running: `docker compose --profile production ps`
   - Check database credentials in `.env`
   - Ensure database container is healthy

3. **Application not accessible**:
   - Check firewall: `sudo ufw status`
   - Verify port binding: `docker compose --profile production ps`
   - Check Nginx configuration: `sudo nginx -t`

4. **High memory usage**:
   - Reduce Celery worker concurrency
   - Adjust Redis memory limit
   - Monitor with `htop` and `docker stats`

### Performance Tuning

1. **For high traffic**:
   - Increase Gunicorn workers: `-w 6` or `-w 8`
   - Add more Celery workers
   - Consider Redis clustering

2. **For low resources**:
   - Reduce worker concurrency: `--concurrency=1`
   - Use fewer Gunicorn workers: `-w 2`
   - Limit Redis memory: `--maxmemory 128mb`

## Backup and Recovery

### Automatic Backups
- Database backups run daily at 2:00 AM
- Backups are compressed and stored in `/opt/corpus-te/backups/`
- Old backups are automatically cleaned up after 7 days

### Manual Backup
```bash
# Full system backup
sudo tar -czf /opt/backups/corpus-te-full-$(date +%Y%m%d).tar.gz \
  /opt/corpus-te \
  --exclude=/opt/corpus-te/backups

# Database only
/opt/corpus-te/backup.sh
```

### Recovery
```bash
# Restore database
cd /opt/corpus-te
gunzip backups/backup_YYYYMMDD_HHMMSS.sql.gz
docker compose --profile production exec -T postgres psql -U postgres -d corpus_te < backups/backup_YYYYMMDD_HHMMSS.sql
```

## Support

If you encounter issues:
1. Check the application logs
2. Verify your environment configuration
3. Ensure all services are running and healthy
4. Check system resources (CPU, RAM, Disk)

For additional help, provide:
- Error messages from logs
- System specifications
- Docker service status
- Environment configuration (without sensitive data)
