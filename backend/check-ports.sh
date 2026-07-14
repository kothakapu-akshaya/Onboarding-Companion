#!/bin/bash

# Port Check Script for Corpus TE Services
# This script checks the port configuration and usage

echo "=== Corpus TE Port Configuration ==="
echo ""

echo "📋 Service Port Mapping:"
echo "  • Main FastAPI App:    8000  (External access)"
echo "  • PostgreSQL Database: 5432  (External access for dev)"
echo "  • Redis Message Broker: 6379 (External access for dev)"
echo "  • Flower (Celery UI):  5555  (External access)"
echo "  • Celery Workers:      -     (No ports needed)"
echo "  • Celery Beat:         -     (No ports needed)"
echo ""

echo "🔍 Checking current port usage..."
echo ""

# Check if ports are in use
check_port() {
    local port=$1
    local service=$2
    
    if ss -tlnp | grep -q ":$port "; then
        echo "  ✅ Port $port ($service): IN USE"
        # Show what's using it
        ss -tlnp | grep ":$port " | awk '{print "     Process: " $7}'
    else
        echo "  ⚪ Port $port ($service): Available"
    fi
}

check_port 8000 "FastAPI App"
check_port 5432 "PostgreSQL"
check_port 6379 "Redis"
check_port 5555 "Flower"

echo ""
echo "🐳 Docker Compose Service Analysis:"
echo ""

# Check if docker-compose files exist and analyze them
if [ -f "docker-compose.yml" ]; then
    echo "📄 Development docker-compose.yml:"
    echo "   App ports: $(grep -A 2 'app:' docker-compose.yml | grep 'ports:' -A 1 | grep -o '[0-9]*:[0-9]*' || echo 'Not found')"
    echo "   Celery worker ports: $(grep -A 10 'celery-worker:' docker-compose.yml | grep 'ports:' || echo 'None (correct)')"
    echo "   Celery beat ports: $(grep -A 10 'celery-beat:' docker-compose.yml | grep 'ports:' || echo 'None (correct)')"
fi

if [ -f "docker-compose.prod.yml" ]; then
    echo ""
    echo "📄 Production docker-compose.prod.yml:"
    echo "   App ports: $(grep -A 5 'app:' docker-compose.prod.yml | grep 'ports:' -A 1 | grep -o '[0-9]*:[0-9]*' || echo 'Not found')"
    echo "   Celery worker ports: $(grep -A 10 'celery-worker:' docker-compose.prod.yml | grep 'ports:' || echo 'None (correct)')"
    echo "   Celery beat ports: $(grep -A 10 'celery-beat:' docker-compose.prod.yml | grep 'ports:' || echo 'None (correct)')"
fi

echo ""
echo "ℹ️  Note: Celery workers and beat schedulers don't need exposed ports."
echo "   They communicate internally via Redis message queues."
echo ""

# Check if services are running in Docker
if command -v docker &> /dev/null; then
    echo "🐳 Currently running Docker containers:"
    docker ps --format "table {{.Names}}\t{{.Ports}}" 2>/dev/null || echo "   No containers running or Docker not accessible"
fi

echo ""
echo "✅ Port configuration appears correct if Celery services show 'None'."
echo "   Only the main app (8000) and Flower (5555) should have exposed ports."
