# Samba Manager Release Workflow Guide

## Overview

This guide describes the complete release process for Samba Manager. The release system provides automated tools for building, validating, publishing, and archiving releases.

## Release Components

### 1. **Version Management** (`version.py`)
- Central version definition
- Version history tracking
- Version information API

### 2. **Release Builder** (`build_release.sh`)
- Creates distribution packages
- Generates checksums and manifests
- Produces multiple formats (tar.gz, zip)

### 3. **Release Validator** (`validate_release.sh`)
- Verifies release integrity
- Checks for required files
- Validates checksums and contents

### 4. **Release Publisher** (`publish_release.sh`)
- Creates GitHub releases
- Uploads distribution files
- Publishes release notes

### 5. **Changelog Generator** (`generate_changelog.sh`)
- Generates changelog from git commits
- Categorizes changes (features, fixes, docs)
- Produces draft changelog

### 6. **Docker Support** (`releases/docker/`)
- Dockerfile for container deployment
- Docker Compose configuration
- Supervisor configuration for service management

## Release Process Workflow

### Step 1: Prepare for Release

#### Update Version
Edit `version.py` and update the version number:
```python
__version__ = "1.3.0"  # Update this
```

#### Update Changelog
Add entries to `RELEASE_NOTES.md` describing the changes:
```markdown
## v1.3.0 - 2026-02-15

### New Features
- Feature 1 description
- Feature 2 description

### Bug Fixes
- Fix 1 description
- Fix 2 description
```

#### Test the Application
```bash
# Run in development mode
python run.py --dev

# Run tests (if available)
# python -m pytest tests/

# Verify installation on clean system (recommended)
```

### Step 2: Build Release Package

```bash
# Make script executable (first time only)
chmod +x build_release.sh

# Build the release
./build_release.sh
```

This generates:
- `releases/stable/samba-manager-1.3.0.tar.gz` - Source archive
- `releases/stable/samba-manager-1.3.0.zip` - ZIP archive
- `releases/stable/RELEASE_NOTES.md` - Release notes
- `releases/stable/checksums.txt` - SHA-256 checksums
- `releases/stable/RELEASE_MANIFEST.md` - Package manifest

### Step 3: Validate Release

```bash
# Make script executable (first time only)
chmod +x validate_release.sh

# Validate the release package
./validate_release.sh
```

Expected output:
```
✓ Archive contains: app
✓ Archive contains: run.py
✓ Archive contains: requirements.txt
✓ All checksums verified
✓ Validation passed!
```

### Step 4: Test Installation

**Option A: Local Testing**
```bash
# Extract and test the release
tar -xzf releases/stable/samba-manager-1.3.0.tar.gz
cd samba-manager-1.3.0

# Test in development mode
python run.py --dev
```

**Option B: Docker Testing**
```bash
# Build Docker image
cd releases/docker
docker build -t samba-manager:test .

# Run container
docker-compose up

# Test in browser: http://localhost:5000
```

**Option C: Virtual Machine Testing**
```bash
# Create a clean VM or container
# Copy release package
# Run installation script
sudo ./install.sh

# Verify service
sudo systemctl status samba-manager
```

### Step 5: Commit and Tag Release

```bash
# Stage changes
git add version.py RELEASE_NOTES.md

# Commit
git commit -m "Release v1.3.0"

# Push to repository
git push origin main

# Create git tag (optional - publish_release.sh will do this)
git tag -a v1.3.0 -m "Release version 1.3.0"
git push origin v1.3.0
```

### Step 6: Generate Changelog

```bash
# Make script executable (first time only)
chmod +x generate_changelog.sh

# Generate changelog from commits
./generate_changelog.sh

# Review and edit
cat CHANGELOG_DRAFT.md

# Move to releases directory
mv CHANGELOG_DRAFT.md releases/stable/CHANGELOG.md
```

### Step 7: Publish Release

```bash
# Prerequisites:
# - GitHub CLI installed: brew install gh
# - Authenticated: gh auth login
# - Changes committed and pushed
# - Git tag created

# Make script executable (first time only)
chmod +x publish_release.sh

# Publish to GitHub
./publish_release.sh
```

This will:
1. Create git tag `v1.3.0`
2. Create GitHub Release
3. Upload distribution files
4. Publish release notes

### Step 8: Post-Release Tasks

#### Update Documentation
- [ ] Update README.md with new version
- [ ] Update INSTALL.md if needed
- [ ] Update TROUBLESHOOTING.md for any known issues
- [ ] Update wiki pages

#### Announce Release
- [ ] Create GitHub announcement
- [ ] Email mailing list (if applicable)
- [ ] Update website/blog
- [ ] Social media announcement

#### Archive Previous Release
```bash
# Move previous release to archive
mkdir -p releases/archive/v1.3.0
mv releases/stable/samba-manager-1.3.0.* releases/archive/v1.3.0/
```

#### Update Docker Hub
```bash
# Push Docker image
docker tag samba-manager:latest lyarinet/samba-manager:1.3.0
docker push lyarinet/samba-manager:1.3.0
docker tag samba-manager:latest lyarinet/samba-manager:latest
docker push lyarinet/samba-manager:latest
```

**View your release**: https://hub.docker.com/r/lyarinet/samba-manager

## Release File Structure

```
releases/
├── stable/                          # Current stable release
│   ├── samba-manager-1.3.0.tar.gz   # Source archive
│   ├── samba-manager-1.3.0.zip      # ZIP archive
│   ├── samba-manager-1.3.0.tar.gz.sha256
│   ├── samba-manager-1.3.0.zip.sha256
│   ├── checksums.txt
│   ├── RELEASE_NOTES.md
│   ├── RELEASE_MANIFEST.md
│   └── CHANGELOG.md
├── beta/                            # Beta releases (optional)
│   ├── samba-manager-1.3.0-beta.1.tar.gz
│   └── ...
├── archive/                         # Previous releases
│   ├── v1.2.0/
│   │   ├── samba-manager-1.2.0.tar.gz
│   │   └── ...
│   └── v1.1.0/
│       └── ...
├── docker/                          # Docker configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── supervisord.conf
│   └── entrypoint.sh
└── README.md                        # Release documentation
```

## Verification Commands

### Verify Checksums
```bash
cd releases/stable
sha256sum -c checksums.txt
```

### Verify Archive Integrity
```bash
# Test TAR.GZ
tar -tzf samba-manager-1.3.0.tar.gz | head -20

# Test ZIP
unzip -t samba-manager-1.3.0.zip | head -20
```

### Verify GitHub Release
```bash
# List releases
gh release list

# View specific release
gh release view v1.3.0

# Download release asset
gh release download v1.3.0 --pattern "*.tar.gz"
```

## Release Versioning

### Version Format
```
MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]

Examples:
1.0.0           # Release
1.2.0           # Minor release
1.2.1           # Patch release
1.3.0-beta.1    # Beta release
1.3.0-rc.1      # Release candidate
```

### Versioning Rules
- **MAJOR**: Incompatible API changes, significant features
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, security patches
- **PRE-RELEASE**: Beta, RC versions for testing
- **BUILD**: Build metadata (optional)

## Release Channels

### Stable Channel
- Production-ready releases
- Thoroughly tested
- Recommended for all users
- Version: `1.2.0`, `1.3.0`, etc.

### Beta Channel
- Pre-release versions
- For testing and feedback
- May contain breaking changes
- Version: `1.3.0-beta.1`, `1.3.0-beta.2`

### RC Channel
- Release candidates
- Near-final testing
- Ready for production deployment
- Version: `1.3.0-rc.1`, `1.3.0-rc.2`

### Development Channel
- Latest code from main branch
- Not recommended for production
- Installation: `git clone && pip install -r requirements.txt`

## Troubleshooting

### Build Script Fails
```bash
# Check Python version
python3 --version  # Should be 3.6+

# Check write permissions
ls -la releases/

# Clear build directory
rm -rf build/
./build_release.sh
```

### Checksum Mismatch
```bash
# Regenerate checksums
cd releases/stable
sha256sum *.tar.gz *.zip > checksums.txt

# Verify
sha256sum -c checksums.txt
```

### GitHub Release Upload Fails
```bash
# Install GitHub CLI
brew install gh  # macOS
sudo apt install gh  # Debian/Ubuntu

# Authenticate
gh auth login

# Verify credentials
gh auth status

# Try publishing again
./publish_release.sh
```

### Docker Build Fails
```bash
# Clean build
docker system prune -a

# Rebuild
cd releases/docker
docker build --no-cache -t samba-manager:latest .
```

## Maintenance

### Monthly Tasks
- [ ] Monitor bug reports
- [ ] Plan next release features
- [ ] Update dependencies
- [ ] Security audits

### Quarterly Tasks
- [ ] Release patch updates
- [ ] Update documentation
- [ ] Performance optimization
- [ ] Community feedback review

### Annually
- [ ] Major version release
- [ ] Architecture review
- [ ] Dependency updates
- [ ] License compliance check

## Support

For questions or issues with the release process:
- Create an issue on GitHub
- Check existing documentation
- Review build and validation scripts
- Test in development mode first

---

**Last Updated**: 2026-01-23
**Version**: 1.2.0
**Maintainer**: Lyarinet
