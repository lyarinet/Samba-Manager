#!/bin/bash
#
# Script to create a release package for Samba Manager
#

# Set version (change this for each release)
VERSION="1.2.0"
RELEASE_NAME="samba-manager-$VERSION"

# Create a temporary directory for the release
echo "Creating release package for Samba Manager v$VERSION..."
mkdir -p build
rm -rf build/$RELEASE_NAME
mkdir -p build/$RELEASE_NAME

# Copy required files
echo "Copying project files..."
cp -r app build/$RELEASE_NAME/
cp -r run.py build/$RELEASE_NAME/
cp -r requirements.txt build/$RELEASE_NAME/
cp -r run_with_sudo.sh build/$RELEASE_NAME/
cp -r README.md build/$RELEASE_NAME/
cp -r LICENSE build/$RELEASE_NAME/
cp -r CONTRIBUTING.md build/$RELEASE_NAME/
cp -r TROUBLESHOOTING.md build/$RELEASE_NAME/ 2>/dev/null || echo "No troubleshooting guide found, skipping..."

# Remove any __pycache__ directories and .pyc files
echo "Cleaning up Python cache files..."
find build/$RELEASE_NAME -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find build/$RELEASE_NAME -name "*.pyc" -type f -delete
find build/$RELEASE_NAME -name "*.pyo" -type f -delete
find build/$RELEASE_NAME -name "*.pyd" -type f -delete
find build/$RELEASE_NAME -name ".DS_Store" -type f -delete

# Create tarball and zip archives
echo "Creating archives..."
cd build
tar -czf $RELEASE_NAME.tar.gz $RELEASE_NAME
cd ..

# Generate SHA-256 checksums
echo "Generating checksums..."
cd build
sha256sum $RELEASE_NAME.tar.gz > $RELEASE_NAME.tar.gz.sha256
cd ..

# Create a release notes template
echo "Generating release notes template..."
cat > build/RELEASE_NOTES.md << EOF
# Samba Manager v$VERSION Release Notes

## Overview

Samba Manager v$VERSION is [brief description of this release].

## New Features

- Feature 1
- Feature 2
- Feature 3

## Bug Fixes

- Fixed issue 1
- Fixed issue 2

## Known Issues

- Known issue 1
- Known issue 2

## Installation

1. Download the appropriate package for your system
2. Extract the archive: \`tar -xzf $RELEASE_NAME.tar.gz\`
3. Install dependencies: \`pip install -r requirements.txt\`
4. Run the application: \`./run_with_sudo.sh\`

## Upgrade Instructions

If upgrading from a previous version:

1. Back up your existing configuration
2. Replace the application files with those from this release
3. Run the application

## SHA-256 Checksums

\`\`\`
$(cat build/$RELEASE_NAME.tar.gz.sha256)
\`\`\`
EOF

echo "Release package created successfully!"
echo "Files are located in the build directory:"
echo "  - build/$RELEASE_NAME.tar.gz"
echo "  - build/RELEASE_NOTES.md (template for release notes)"
echo ""
echo "Next steps:"
echo "1. Review and edit the release notes in build/RELEASE_NOTES.md"
echo "2. Create a new release on GitHub and upload these files"
echo "3. Copy the contents of the release notes to the GitHub release description" 