#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# build.sh — one-shot APK builder
# Run this on Ubuntu 22.04 / Debian 12 / WSL2 (Ubuntu).
# First build takes ~25 min (downloads Android SDK + NDK).
# Subsequent builds: ~3 min.
# The finished APK lands in:  bin/batterymonitor-1.0-debug.apk
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "==> Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y \
    git zip unzip openjdk-17-jdk \
    python3-pip python3-venv \
    libffi-dev libssl-dev \
    autoconf libtool pkg-config \
    build-essential ccache

echo "==> Installing Python build tools..."
pip3 install --upgrade pip
pip3 install buildozer cython

echo "==> Building APK (this will take a while the first time)..."
buildozer android debug

echo ""
echo "Done!  APK is at:"
ls bin/*.apk
