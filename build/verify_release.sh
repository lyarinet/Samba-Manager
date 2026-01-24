#!/bin/bash

# Installation Verification Script for Samba Manager
# This script verifies that the installation is correct

echo "Samba Manager Installation Verification"
echo "========================================"
echo ""

errors=0
warnings=0

# Check Python installation
echo "Checking Python installation..."
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version)
    echo "✓ Python found: $python_version"
    
    python_minor=$(python3 -c 'import sys; print(sys.version_info[1])')
    if [ "$python_minor" -lt 6 ]; then
        echo "✗ Python 3.6+ required, found 3.$python_minor"
        ((errors++))
    fi
else
    echo "✗ Python 3 not found"
    ((errors++))
fi

# Check Samba installation
echo ""
echo "Checking Samba installation..."
if command -v smbclient &> /dev/null; then
    samba_version=$(smbclient --version 2>&1 | head -n1)
    echo "✓ Samba found: $samba_version"
else
    echo "⚠ Samba client not found (may not be required)"
    ((warnings++))
fi

# Check Flask installation
echo ""
echo "Checking Flask installation..."
if python3 -c "import flask" 2>/dev/null; then
    flask_version=$(python3 -c "import flask; print(flask.__version__)")
    echo "✓ Flask found: $flask_version"
else
    echo "✗ Flask not installed"
    ((errors++))
fi

# Check required Python modules
echo ""
echo "Checking required Python modules..."
required_modules=("flask_login" "flask_limiter" "flask_wtf" "werkzeug")
for module in "${required_modules[@]}"; do
    if python3 -c "import ${module}" 2>/dev/null; then
        echo "✓ $module found"
    else
        echo "✗ $module not found"
        ((errors++))
    fi
done

# Check port availability
echo ""
echo "Checking port 5000 availability..."
if netstat -tuln 2>/dev/null | grep -q ":5000 "; then
    echo "⚠ Port 5000 appears to be in use"
    ((warnings++))
else
    echo "✓ Port 5000 appears available"
fi

# Summary
echo ""
echo "========================================"
echo "Verification Summary"
echo "========================================"
echo "Errors: $errors"
echo "Warnings: $warnings"

if [ $errors -eq 0 ]; then
    echo "✓ Installation verified successfully!"
    exit 0
else
    echo "✗ Installation verification failed"
    exit 1
fi
