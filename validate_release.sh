#!/bin/bash
#
# Release Validation Script for Samba Manager
# Validates release integrity and completeness
#

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_section() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

VERSION=$(python3 -c "from version import __version__; print(__version__)")
RELEASE_DIR="releases/stable"

errors=0
warnings=0

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Samba Manager Release Validation${NC}"
echo -e "${BLUE}Version: ${VERSION}${NC}"
echo -e "${BLUE}========================================${NC}"

# Check release directory
print_section "Checking release directory"
if [ ! -d "$RELEASE_DIR" ]; then
    print_error "Release directory not found: $RELEASE_DIR"
    ((errors++))
else
    print_success "Release directory exists"
fi

# Check for required files
print_section "Checking for required files"

required_files=(
    "$RELEASE_DIR/samba-manager-${VERSION}.tar.gz"
    "$RELEASE_DIR/samba-manager-${VERSION}.zip"
    "$RELEASE_DIR/RELEASE_NOTES.md"
    "$RELEASE_DIR/checksums.txt"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        print_success "Found: $(basename $file) ($size)"
    else
        print_error "Missing: $(basename $file)"
        ((errors++))
    fi
done

# Verify checksums
print_section "Verifying checksums"
if [ -f "$RELEASE_DIR/checksums.txt" ]; then
    cd "$RELEASE_DIR"
    if sha256sum -c checksums.txt > /dev/null 2>&1; then
        print_success "All checksums verified"
    else
        print_error "Checksum verification failed"
        ((errors++))
    fi
    cd - > /dev/null
else
    print_warning "No checksums file found"
    ((warnings++))
fi

# Check archive contents
print_section "Checking archive contents"

if [ -f "$RELEASE_DIR/samba-manager-${VERSION}.tar.gz" ]; then
    # Extract to temp directory
    tmpdir=$(mktemp -d)
    tar -xzf "$RELEASE_DIR/samba-manager-${VERSION}.tar.gz" -C "$tmpdir"
    
    cd "$tmpdir/samba-manager-${VERSION}"
    
    required_files_in_archive=(
        "app"
        "run.py"
        "requirements.txt"
        "README.md"
        "LICENSE"
        "MANIFEST.txt"
    )
    
    for file in "${required_files_in_archive[@]}"; do
        if [ -e "$file" ]; then
            print_success "Archive contains: $file"
        else
            print_error "Archive missing: $file"
            ((errors++))
        fi
    done
    
    # Check for unwanted files
    print_section "Checking for excluded files"
    
    if [ -d "__pycache__" ]; then
        print_warning "Archive contains __pycache__ (should be cleaned)"
        ((warnings++))
    else
        print_success "No __pycache__ directories"
    fi
    
    if [ -d ".git" ]; then
        print_warning "Archive contains .git directory (should be excluded)"
        ((warnings++))
    else
        print_success "No .git directory"
    fi
    
    if [ -f "*.pyc" ]; then
        print_warning "Archive contains .pyc files"
        ((warnings++))
    else
        print_success "No .pyc files"
    fi
    
    # Check file permissions
    print_section "Checking file permissions"
    
    if [ -x "run.py" ]; then
        print_warning "run.py is executable (may not be necessary)"
    else
        print_success "run.py has correct permissions"
    fi
    
    # Check documentation
    print_section "Checking documentation"
    
    if grep -q "Version\|version\|${VERSION}" README.md 2>/dev/null; then
        print_success "README.md mentions version"
    else
        print_warning "README.md may not be version-specific"
        ((warnings++))
    fi
    
    cd - > /dev/null
    rm -rf "$tmpdir"
fi

# Check release notes
print_section "Checking release notes"

if [ -f "$RELEASE_DIR/RELEASE_NOTES.md" ]; then
    if grep -q "${VERSION}" "$RELEASE_DIR/RELEASE_NOTES.md"; then
        print_success "Release notes contain version number"
    else
        print_warning "Release notes may not be version-specific"
        ((warnings++))
    fi
    
    if grep -q "Installation\|Requirements\|Features" "$RELEASE_DIR/RELEASE_NOTES.md"; then
        print_success "Release notes contain standard sections"
    else
        print_warning "Release notes may be incomplete"
        ((warnings++))
    fi
else
    print_warning "RELEASE_NOTES.md not found"
    ((warnings++))
fi

# Check git status
print_section "Checking git repository"

if git rev-parse --git-dir > /dev/null 2>&1; then
    print_success "Git repository found"
    
    if git rev-parse "v${VERSION}" > /dev/null 2>&1; then
        print_success "Git tag v${VERSION} exists"
    else
        print_warning "Git tag v${VERSION} not found"
        ((warnings++))
    fi
else
    print_warning "Not in a git repository"
    ((warnings++))
fi

# Summary
print_section "Validation Summary"
echo ""
echo -e "Errors:   ${RED}$errors${NC}"
echo -e "Warnings: ${YELLOW}$warnings${NC}"
echo ""

if [ $errors -eq 0 ]; then
    echo -e "${GREEN}✓ Validation passed!${NC}"
    if [ $warnings -gt 0 ]; then
        echo -e "${YELLOW}Note: $warnings warning(s) found${NC}"
    fi
    exit 0
else
    echo -e "${RED}✗ Validation failed with $errors error(s)${NC}"
    exit 1
fi
