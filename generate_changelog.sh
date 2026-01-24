#!/bin/bash
#
# Release Changelog Generator for Samba Manager
# Generates changelog from git commits since last release
#

set -e

# Color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Get current version
VERSION=$(python3 -c "from version import __version__; print(__version__)")

print_header "Generating Changelog for v${VERSION}"

# Get the last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

if [ -z "$LAST_TAG" ]; then
    print_header "First Release - All Commits"
    COMMITS=$(git log --pretty=format:"- %h - %s (%an)")
else
    print_header "Commits since $LAST_TAG"
    COMMITS=$(git log "$LAST_TAG"..HEAD --pretty=format:"- %h - %s (%an)")
fi

# Categorize commits
FEATURES=$(echo "$COMMITS" | grep -E "feat|feature" || echo "")
FIXES=$(echo "$COMMITS" | grep -E "fix|fixed" || echo "")
DOCS=$(echo "$COMMITS" | grep -E "docs|documentation" || echo "")
OTHER=$(echo "$COMMITS" | grep -v -E "feat|feature|fix|fixed|docs|documentation" || echo "")

# Generate changelog file
cat > CHANGELOG_DRAFT.md << EOF
# Changelog - Version ${VERSION}

## New Features

$(if [ -n "$FEATURES" ]; then echo "$FEATURES"; else echo "- No new features"; fi)

## Bug Fixes

$(if [ -n "$FIXES" ]; then echo "$FIXES"; else echo "- No bug fixes"; fi)

## Documentation

$(if [ -n "$DOCS" ]; then echo "$DOCS"; else echo "- No documentation updates"; fi)

## Other Changes

$(if [ -n "$OTHER" ]; then echo "$OTHER"; else echo "- No other changes"; fi)

## Statistics

- Total Commits: $(echo "$COMMITS" | wc -l)
- Contributors: $(git log "$LAST_TAG"..HEAD --pretty=format:"%an" 2>/dev/null | sort -u | wc -l)

EOF

print_success "Changelog generated: CHANGELOG_DRAFT.md"
echo ""
echo "Please review CHANGELOG_DRAFT.md and edit as needed."
echo "Move to releases/stable/CHANGELOG.md when ready."
