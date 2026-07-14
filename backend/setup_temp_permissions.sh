#!/bin/bash

# Script to set up proper permissions for temp directory used by Docker containers

set -e

# Default temp directory
TEMP_DIR="${TEMP_DIR:-/tmp}"

echo "🔧 Setting up permissions for temp directory: $TEMP_DIR"

# Create the temp directory if it doesn't exist
if [ ! -d "$TEMP_DIR" ]; then
    echo "📁 Creating temp directory: $TEMP_DIR"
    sudo mkdir -p "$TEMP_DIR"
fi

# Create subdirectories needed by the application
echo "📁 Creating application subdirectories..."
sudo mkdir -p "$TEMP_DIR/chunks"
sudo mkdir -p "$TEMP_DIR/staging"
sudo mkdir -p "$TEMP_DIR/logs"

# Get the actual UID of appuser from the container
echo "🔍 Determining appuser UID from container..."
APPUSER_UID=$(docker compose exec -T app id -u appuser 2>/dev/null || echo "1000")
echo "📋 Detected appuser UID: $APPUSER_UID"

# Set proper ownership
echo "🔐 Setting ownership to UID $APPUSER_UID (appuser)..."
sudo chown -R "$APPUSER_UID:$APPUSER_UID" "$TEMP_DIR/chunks"
sudo chown -R "$APPUSER_UID:$APPUSER_UID" "$TEMP_DIR/staging"
sudo chown -R "$APPUSER_UID:$APPUSER_UID" "$TEMP_DIR/logs"

# Set proper permissions
echo "🔐 Setting permissions..."
sudo chmod -R 755 "$TEMP_DIR/chunks"
sudo chmod -R 755 "$TEMP_DIR/staging"
sudo chmod -R 755 "$TEMP_DIR/logs"

# Also ensure the parent directory has proper permissions
echo "🔐 Setting parent directory permissions..."
sudo chmod 755 "$TEMP_DIR"

echo "✅ Temp directory setup complete!"
echo "   Directory: $TEMP_DIR"
echo "   Subdirectories: chunks, staging, logs"
echo "   Owner: UID $APPUSER_UID (appuser)"
echo "   Permissions: 755"

# Show the current state
echo ""
echo "📊 Current directory state:"
ls -la "$TEMP_DIR/" | grep -E "(chunks|staging|logs)" 