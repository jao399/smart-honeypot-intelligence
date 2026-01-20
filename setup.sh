#!/bin/bash
# Smart Honeypot Intelligence - Setup Script (Linux/Mac)
# Automated setup for distribution package

echo ""
echo "====================================="
echo "Smart Honeypot Intelligence Setup"
echo "====================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "[1/3] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies"
    exit 1
fi
echo "✓ Dependencies installed successfully"

echo ""
echo "[2/3] Verifying data files..."
[ ! -d "data" ] && echo "Warning: data folder not found"
[ ! -d "snapshots" ] && echo "Warning: snapshots folder not found"
echo "✓ File verification complete"

echo ""
echo "[3/3] Starting application..."
echo ""
echo "====================================="
echo "The app will open at: http://localhost:8501"
echo "Press Ctrl+C to stop the application"
echo "====================================="
echo ""

streamlit run app.py
