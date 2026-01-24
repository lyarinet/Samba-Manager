#!/bin/bash
#
# Comprehensive Release Pack Builder for Samba Manager
# Creates multiple distribution formats with verification
#

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get version from version.py
VERSION=$(python3 -c "from version import __version__; print(__version__)")
RELEASE_NAME="samba-manager-${VERSION}"
BUILD_DIR="build"
RELEASE_DIR="releases/stable"
DIST_DIR="${BUILD_DIR}/dist"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Samba Manager Release Pack Builder${NC}"
echo -e "${BLUE}Version: ${VERSION}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to print section headers
print_section() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

# Function to print info messages
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Cleanup previous builds
print_section "Cleaning up previous builds"
rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}" "${RELEASE_DIR}"
print_success "Build directories prepared"

# Create release directory structure
print_section "Creating release package structure"
mkdir -p "${BUILD_DIR}/${RELEASE_NAME}"

# Copy required files
echo "Copying application files..."
cp -r app "${BUILD_DIR}/${RELEASE_NAME}/"
cp run.py "${BUILD_DIR}/${RELEASE_NAME}/"
cp version.py "${BUILD_DIR}/${RELEASE_NAME}/"
cp requirements.txt "${BUILD_DIR}/${RELEASE_NAME}/"
cp pyproject.toml "${BUILD_DIR}/${RELEASE_NAME}/"
cp README.md "${BUILD_DIR}/${RELEASE_NAME}/"
cp LICENSE "${BUILD_DIR}/${RELEASE_NAME}/"
cp CONTRIBUTING.md "${BUILD_DIR}/${RELEASE_NAME}/"
cp INSTALL.md "${BUILD_DIR}/${RELEASE_NAME}/"
cp TROUBLESHOOTING.md "${BUILD_DIR}/${RELEASE_NAME}/"
cp TERMINAL.md "${BUILD_DIR}/${RELEASE_NAME}/"
cp install.sh "${BUILD_DIR}/${RELEASE_NAME}/"
cp run_with_sudo.sh "${BUILD_DIR}/${RELEASE_NAME}/"
cp Dockerfile "${BUILD_DIR}/${RELEASE_NAME}/"
cp smb.conf.template "${BUILD_DIR}/${RELEASE_NAME}/"
print_success "Application files copied"

# Create MANIFEST.txt
print_info "Creating MANIFEST.txt"
cat > "${BUILD_DIR}/${RELEASE_NAME}/MANIFEST.txt" << 'EOF'
Samba Manager Release Package Manifest
======================================

Core Application:
  app/                    - Main Flask application package
  run.py                  - Application entry point
  version.py              - Version information
  requirements.txt        - Python dependencies
  pyproject.toml          - Project configuration

Documentation:
  README.md               - Main documentation and features
  INSTALL.md              - Installation instructions
  CONTRIBUTING.md         - Contribution guidelines
  TROUBLESHOOTING.md      - Troubleshooting guide
  TERMINAL.md             - Terminal feature documentation

Installation & Deployment:
  install.sh              - Installation script
  run_with_sudo.sh        - Run with sudo permissions
  Dockerfile              - Docker container definition
  smb.conf.template       - Samba configuration template

License:
  LICENSE                 - MIT License

This package includes everything needed to deploy Samba Manager.
EOF
print_success "MANIFEST.txt created"

# Clean up Python cache files
print_section "Cleaning up cache files"
find "${BUILD_DIR}/${RELEASE_NAME}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "${BUILD_DIR}/${RELEASE_NAME}" -name "*.pyc" -type f -delete
find "${BUILD_DIR}/${RELEASE_NAME}" -name "*.pyo" -type f -delete
find "${BUILD_DIR}/${RELEASE_NAME}" -name "*.pyd" -type f -delete
find "${BUILD_DIR}/${RELEASE_NAME}" -name ".DS_Store" -type f -delete
find "${BUILD_DIR}/${RELEASE_NAME}" -name ".git*" -type f -delete
print_success "Cache files removed"

# Create TAR.GZ archive
print_section "Creating TAR.GZ archive"
cd "${BUILD_DIR}"
tar -czf "${RELEASE_NAME}.tar.gz" "${RELEASE_NAME}"
cd ..
mv "${BUILD_DIR}/${RELEASE_NAME}.tar.gz" "${DIST_DIR}/"
print_success "Created: ${RELEASE_NAME}.tar.gz"

# Create ZIP archive
print_section "Creating ZIP archive"
cd "${BUILD_DIR}"
zip -r -q "${RELEASE_NAME}.zip" "${RELEASE_NAME}"
cd ..
mv "${BUILD_DIR}/${RELEASE_NAME}.zip" "${DIST_DIR}/"
print_success "Created: ${RELEASE_NAME}.zip"

# Generate checksums
print_section "Generating checksums"
cd "${DIST_DIR}"

# SHA-256 checksums
sha256sum ${RELEASE_NAME}.tar.gz > ${RELEASE_NAME}.tar.gz.sha256
sha256sum ${RELEASE_NAME}.zip > ${RELEASE_NAME}.zip.sha256
cat ${RELEASE_NAME}.tar.gz.sha256 ${RELEASE_NAME}.zip.sha256 > checksums.txt

print_success "SHA-256 checksums generated"
echo ""
echo "Checksums:"
cat checksums.txt

cd ../..

# Create release notes
print_section "Creating release notes"
cat > "${DIST_DIR}/RELEASE_NOTES.md" << EOF
# Samba Manager v${VERSION} Release Notes

**Release Date**: $(date +%Y-%m-%d)

## Overview

This release of Samba Manager includes all features and improvements up to version ${VERSION}.

## What's Included

This release package includes:
- Complete Samba Manager web application
- Installation scripts for multiple distributions
- Docker configuration for containerized deployment
- Comprehensive documentation
- Configuration templates

## Installation

### Quick Start
\`\`\`bash
# Extract the package
tar -xzf ${RELEASE_NAME}.tar.gz
cd ${RELEASE_NAME}

# Run the installation
sudo ./install.sh
\`\`\`

### Docker Deployment
\`\`\`bash
docker build -t samba-manager:${VERSION} .
docker run -p 5000:5000 -v /etc/samba:/etc/samba samba-manager:${VERSION}
\`\`\`

## System Requirements

- **OS**: Linux (Ubuntu, Debian, Fedora, RHEL, CentOS, Arch, Manjaro)
- **Python**: 3.6 or higher
- **Samba**: 4.0 or higher
- **RAM**: Minimum 512 MB
- **Disk**: Minimum 100 MB
- **Network**: Port 5000 (configurable)

## Supported Distributions

✓ Ubuntu 20.04 LTS, 22.04 LTS, 24.04 LTS
✓ Debian 11, 12
✓ Fedora 37, 38, 39
✓ RHEL/CentOS 8, 9
✓ Arch Linux
✓ Manjaro

## Verification

To verify the integrity of this release, check the checksums:

\`\`\`bash
sha256sum -c checksums.txt
\`\`\`

All files should show "OK".

## Documentation

- **README.md**: Features and overview
- **INSTALL.md**: Detailed installation instructions
- **TROUBLESHOOTING.md**: Common issues and solutions
- **CONTRIBUTING.md**: Contribution guidelines
- **TERMINAL.md**: Terminal access feature documentation

## Known Limitations

- Requires sudo access for configuration changes
- Single-machine management only (no federation)
- Web interface requires JavaScript enabled

## Upgrading

If upgrading from a previous version:

1. Backup your configuration:
   \`\`\`bash
   sudo cp -r /etc/samba /etc/samba.backup.\$(date +%Y%m%d)
   \`\`\`

2. Extract and install the new version:
   \`\`\`bash
   tar -xzf ${RELEASE_NAME}.tar.gz
   cd ${RELEASE_NAME}
   sudo ./install.sh
   \`\`\`

3. Restart the service:
   \`\`\`bash
   sudo systemctl restart samba-manager
   \`\`\`

## Support

- **Issues**: https://github.com/lyarinet/Samba-Manager/issues
- **Discussions**: https://github.com/lyarinet/Samba-Manager/discussions
- **Documentation**: https://github.com/lyarinet/Samba-Manager/wiki

## License

This software is released under the MIT License. See the LICENSE file for details.

## Contributors

- Lyarinet - Project founder and maintainer

---

**Download**: https://github.com/lyarinet/Samba-Manager/releases/tag/v${VERSION}

EOF
print_success "Release notes created"

# Create installation verification script
print_section "Creating verification script"
cat > "${BUILD_DIR}/verify_release.sh" << 'EOF'
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
EOF

chmod +x "${BUILD_DIR}/verify_release.sh"
cp "${BUILD_DIR}/verify_release.sh" "${DIST_DIR}/"
print_success "Verification script created"

# Generate release manifest
print_section "Generating release manifest"
cat > "${RELEASE_DIR}/RELEASE_MANIFEST.md" << EOF
# Samba Manager ${VERSION} Release Manifest

**Release Date**: $(date)
**Build System**: $(uname -s)
**Release Manager**: Release Pack Builder Script

## Package Contents

### Archives
- **${RELEASE_NAME}.tar.gz** (GNU tar + gzip)
  - Size: $(du -h "${DIST_DIR}/${RELEASE_NAME}.tar.gz" | cut -f1)
  - SHA256: $(cat "${DIST_DIR}/${RELEASE_NAME}.tar.gz.sha256" | awk '{print $1}')

- **${RELEASE_NAME}.zip** (ZIP format)
  - Size: $(du -h "${DIST_DIR}/${RELEASE_NAME}.zip" | cut -f1)
  - SHA256: $(cat "${DIST_DIR}/${RELEASE_NAME}.zip.sha256" | awk '{print $1}')

### Documentation
- RELEASE_NOTES.md - Release notes and installation guide
- MANIFEST.txt - Package contents listing

### Verification
- checksums.txt - SHA-256 checksums for all packages
- verify_release.sh - Installation verification script

## System Requirements

- Linux distribution (Ubuntu, Debian, Fedora, RHEL, CentOS, Arch, Manjaro)
- Python 3.6+
- Samba 4.0+
- 512 MB RAM minimum
- 100 MB disk space minimum

## Installation Methods

1. **Automated Installation**
   \`\`\`bash
   tar -xzf ${RELEASE_NAME}.tar.gz
   cd ${RELEASE_NAME}
   sudo ./install.sh
   \`\`\`

2. **Docker Deployment**
   \`\`\`bash
   cd ${RELEASE_NAME}
   docker build -t samba-manager:${VERSION} .
   docker run -p 5000:5000 -v /etc/samba:/etc/samba samba-manager:${VERSION}
   \`\`\`

## Checksum Verification

Verify package integrity before installation:

\`\`\`bash
sha256sum -c checksums.txt
\`\`\`

Expected output:
\`\`\`
${RELEASE_NAME}.tar.gz: OK
${RELEASE_NAME}.zip: OK
\`\`\`

## Quick Start

After installation:

1. Start the service:
   \`\`\`bash
   sudo systemctl start samba-manager
   \`\`\`

2. Access the web interface:
   - URL: http://localhost:5000
   - Browser: Chrome, Firefox, Safari, Edge (latest versions)

3. Login with your credentials (set during installation)

## Support Resources

- **GitHub**: https://github.com/lyarinet/Samba-Manager
- **Issues**: https://github.com/lyarinet/Samba-Manager/issues
- **Wiki**: https://github.com/lyarinet/Samba-Manager/wiki

## License

This software is distributed under the MIT License.
See LICENSE file in the package for details.

---

Built by: Release Pack Builder Script
Build Date: $(date +%Y-%m-%d\ %H:%M:%S)

EOF

print_success "Release manifest created"

# Copy all distributions to releases directory
print_section "Organizing release files"
cp "${DIST_DIR}"/* "${RELEASE_DIR}/" 2>/dev/null || true

# Create checksums for releases directory
cd "${RELEASE_DIR}"
sha256sum *.tar.gz *.zip > checksums.txt 2>/dev/null || true
cd - > /dev/null

print_success "Files organized in ${RELEASE_DIR}/"

# Summary
print_section "Release Build Summary"
echo ""
echo "Release Version: ${BLUE}${VERSION}${NC}"
echo "Release Name: ${BLUE}${RELEASE_NAME}${NC}"
echo "Build Date: ${BLUE}$(date)${NC}"
echo ""
echo "Generated Files:"
ls -lh "${RELEASE_DIR}" | grep -v "^total" | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "Installation Instructions:"
echo "  1. Download: samba-manager-${VERSION}.tar.gz"
echo "  2. Extract: tar -xzf samba-manager-${VERSION}.tar.gz"
echo "  3. Install: cd samba-manager-${VERSION} && sudo ./install.sh"
echo ""
echo "Verification:"
echo "  sha256sum -c releases/stable/checksums.txt"
echo ""
print_success "Release pack build completed successfully!"
echo ""
echo "Next Steps:"
echo "  1. Review RELEASE_NOTES.md"
echo "  2. Upload to GitHub Releases"
echo "  3. Publish release announcement"
echo "  4. Update documentation"
echo ""
