#!/bin/bash
# Build script for KRYZENSYS Recon Platform
# Avoids mise Python 3.11.9 issue on Netlify

set -e

echo "🚀 KRYZENSYS Recon Platform - Build Script"
echo "==========================================="

# Check if we're on Netlify
if [ -n "$NETLIFY" ]; then
  echo "📍 Detected Netlify build environment"
  export NETLIFY=true
  # Use Netlify's bundled Python 3.11 instead of mise
  PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
  NODE_VERSION="${NODE_VERSION:-20}"
else
  echo "📍 Local build environment"
  PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
  NODE_VERSION="${NODE_VERSION:-20}"
fi

# Try to find Python
PYTHON_BIN=""
for cmd in python3 python python3.11 python3.10 python3.12; do
  if command -v "$cmd" >/dev/null 2>&1; then
    PYTHON_BIN="$cmd"
    echo "✅ Found Python: $($cmd --version 2>&1)"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "⚠️ No Python found - frontend only build"
fi

# Frontend build
echo ""
echo "📦 Building frontend..."
cd "$(dirname "$0")/frontend" || cd frontend

# Install Node deps if package.json exists
if [ -f "package.json" ]; then
  echo "📥 Installing Node dependencies..."
  npm ci --no-audit --no-fund || npm install --no-audit --no-fund
fi

# Process HTML files (any templating if needed)
echo "📝 Processing HTML files..."
for html in *.html admin/*.html; do
  if [ -f "$html" ]; then
    # Replace placeholders
    sed -i.bak \
      -e "s|ADMIN_EMAIL|f91186645@gmail.com|g" \
      -e "s|ADMIN_GITHUB|https://github.com/KRYZENSYS/|g" \
      -e "s|ADMIN_TELEGRAM|https://t.me/FirdavsVIP|g" \
      "$html" 2>/dev/null || true
  fi
done

# Copy PWA assets
echo "📱 Setting up PWA..."
mkdir -p pwa
[ -f "pwa/manifest.json" ] && echo "✅ PWA manifest ready"
[ -f "pwa/sw.js" ] && echo "✅ Service Worker ready"

# Copy admin assets
echo "🔐 Setting up admin panel..."
mkdir -p admin
[ -f "admin/index.html" ] && echo "✅ Admin panel ready"

echo ""
echo "✅ Build completed successfully!"
echo "==========================================="
