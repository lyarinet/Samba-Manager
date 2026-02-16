#!/bin/bash
#
# Release Publication Script for Samba Manager
# Publishes releases to GitHub and updates documentation
#

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    exit 1
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Get version
VERSION=$(python3 -c "from version import __version__; print(__version__)")
RELEASE_DIR="releases/stable"

print_header "Samba Manager Release Publication"

# Check if release files exist
print_info "Checking for release files..."
if [ ! -d "$RELEASE_DIR" ] || [ -z "$(ls -A $RELEASE_DIR)" ]; then
    print_error "No release files found in $RELEASE_DIR"
fi

# Check GitHub CLI
print_info "Checking GitHub CLI..."
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed. Install with: brew install gh"
fi

# Check Git
if ! command -v git &> /dev/null; then
    print_error "Git is not installed"
fi

# Verify we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a git repository"
fi

# Get current git status
print_info "Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    print_error "Working directory is not clean. Commit or stash changes first."
fi

# Create git tag
print_header "Creating Git Tag"
TAG_NAME="v${VERSION}"

if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    print_info "Tag $TAG_NAME already exists"
else
    print_info "Creating tag $TAG_NAME..."
    git tag -a "$TAG_NAME" -m "Release version $VERSION"
    git push origin "$TAG_NAME"
    print_success "Tag created and pushed"
fi

# Prepare release notes
print_header "Preparing Release Notes"

if [ -f "$RELEASE_DIR/RELEASE_NOTES.md" ]; then
    RELEASE_NOTES=$(cat "$RELEASE_DIR/RELEASE_NOTES.md")
    print_success "Release notes prepared"
else
    print_error "RELEASE_NOTES.md not found in $RELEASE_DIR"
fi

# Get checksums
CHECKSUMS=$(cat "$RELEASE_DIR/checksums.txt" 2>/dev/null || echo "Checksums not available")

# Create GitHub Release
print_header "Creating GitHub Release"

print_info "Creating release: $TAG_NAME"

# Check if release already exists
if gh release view "$TAG_NAME" >/dev/null 2>&1; then
    print_info "Release $TAG_NAME already exists"
    read -p "Delete and recreate? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        gh release delete "$TAG_NAME" -y
        print_info "Deleted previous release"
    else
        print_info "Keeping existing release"
        exit 0
    fi
fi

# Upload release with files
print_info "Uploading release files..."

gh release create "$TAG_NAME" \
    "$RELEASE_DIR"/*.tar.gz \
    "$RELEASE_DIR"/*.zip \
    "$RELEASE_DIR"/checksums.txt \
    "$RELEASE_DIR/RELEASE_NOTES.md" \
    --title "Samba Manager v${VERSION}" \
    --notes "$RELEASE_NOTES" \
    || print_error "Failed to create release"

print_success "GitHub release created successfully"

# Display release URL
print_header "Release Published"
echo -e "${GREEN}Release successfully published!${NC}"
echo ""
echo "Release URL: https://github.com/lyarinet/samba-manager/releases/tag/v${VERSION}"
echo ""
echo "Files uploaded:"
ls -1 "$RELEASE_DIR"/*.tar.gz "$RELEASE_DIR"/*.zip 2>/dev/null | xargs -I {} basename {}
echo ""
echo "Verification:"
echo "  sha256sum -c releases/stable/checksums.txt"
echo ""
print_success "Release process complete!"
