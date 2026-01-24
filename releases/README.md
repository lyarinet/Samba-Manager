# Samba Manager Release Packages

This directory contains release packages and tools for distributing Samba Manager.

## Release Formats

### 1. **Source Distribution** (Recommended for most users)
- **Format**: `samba-manager-{version}.tar.gz` and `.zip`
- **Contents**: Complete source code with all dependencies
- **Size**: ~5-10 MB
- **Installation**: Extract and run installation script
- **Best for**: Direct deployment, custom installations, development environments

### 2. **Docker Image**
- **Format**: Docker container image
- **Contents**: Complete application with all dependencies pre-installed
- **Size**: ~500 MB (compressed)
- **Usage**: `docker run -p 5000:5000 samba-manager:latest`
- **Best for**: Containerized environments, quick deployment

### 3. **Debian Package** (Optional)
- **Format**: `.deb` package
- **Contents**: Application installed to system directories
- **Size**: ~20-30 MB
- **Installation**: `sudo apt install ./samba-manager-{version}.deb`
- **Best for**: Ubuntu/Debian systems, system package management

## Directory Structure

```
releases/
├── stable/              # Latest stable release
├── beta/                # Beta and RC releases
├── archive/             # Previous releases
├── docker/              # Docker build files
├── signatures/          # GPG signatures for packages
└── checksums.txt        # SHA-256 checksums for all releases
```

## Downloading Releases

### From GitHub Releases
Visit: https://github.com/lyarinet/Samba-Manager/releases

### Direct Download
```bash
# Latest stable release
wget https://github.com/lyarinet/Samba-Manager/releases/download/v1.2.0/samba-manager-1.2.0.tar.gz

# Verify checksum
wget https://github.com/lyarinet/Samba-Manager/releases/download/v1.2.0/samba-manager-1.2.0.tar.gz.sha256
sha256sum -c samba-manager-1.2.0.tar.gz.sha256
```

## Installation Methods

### Method 1: One-Line Installation (Recommended)
```bash
curl -sSL https://raw.githubusercontent.com/lyarinet/Samba-Manager/main/auto_install.sh | sudo bash
```

### Method 2: Manual Installation from Release Package
```bash
# Extract the release
tar -xzf samba-manager-1.2.0.tar.gz
cd samba-manager-1.2.0

# Run installation
sudo ./install.sh
```

### Method 3: Docker Installation
```bash
docker pull lyarinet/samba-manager:1.2.0
docker run -d \
  -p 5000:5000 \
  -v /etc/samba:/etc/samba:ro \
  -v /var/log/samba:/var/log/samba:ro \
  --name samba-manager \
  lyarinet/samba-manager:1.2.0
```

### Method 4: Debian Package Installation
```bash
sudo apt update
sudo apt install ./samba-manager_1.2.0_amd64.deb
```

## Verification

### Verify Checksum (Recommended)
```bash
# Linux/Mac
sha256sum -c samba-manager-1.2.0.tar.gz.sha256

# Windows (PowerShell)
(Get-FileHash samba-manager-1.2.0.tar.gz).Hash -eq (Get-Content samba-manager-1.2.0.tar.gz.sha256).Split()[0]
```

### Verify GPG Signature
```bash
# Import public key
gpg --import releases/signatures/public-key.asc

# Verify signature
gpg --verify samba-manager-1.2.0.tar.gz.sig samba-manager-1.2.0.tar.gz
```

## Release Channels

### Stable (Production)
- Version: `1.2.0`
- Status: Recommended for production use
- Update frequency: Every 3-6 months
- Download: `releases/stable/`

### Beta
- Version: `1.2.0-beta.1` and higher
- Status: Pre-release, testing recommended
- Update frequency: As needed
- Download: `releases/beta/`

### Development
- Status: Latest code from `main` branch
- Installation: `git clone` and install from source
- Use only for testing and development

## Requirements by Installation Method

| Method | Python | Samba | Go | Docker | Sudo |
|--------|--------|-------|----|----|------|
| Source | ✓ | ✓ |  | | ✓ |
| Docker | | ✓ | ✓ | ✓ | |
| Debian | | ✓ | | | ✓ |
| One-Line | ✓ | | | | ✓ |

## Supported Linux Distributions

- **Ubuntu** 20.04 LTS, 22.04 LTS, 24.04 LTS
- **Debian** 11, 12
- **Fedora** 37, 38, 39
- **RHEL/CentOS** 8, 9
- **Arch Linux** (Latest)
- **Manjaro** (Latest)

## Checksum Verification

All release packages include SHA-256 checksums. Verify downloads before installation:

```bash
# Download package and checksum
wget https://github.com/lyarinet/Samba-Manager/releases/download/v1.2.0/samba-manager-1.2.0.tar.gz
wget https://github.com/lyarinet/Samba-Manager/releases/download/v1.2.0/samba-manager-1.2.0.tar.gz.sha256

# Verify
sha256sum -c samba-manager-1.2.0.tar.gz.sha256
# Output should be: samba-manager-1.2.0.tar.gz: OK
```

## Upgrading from Previous Versions

```bash
# Backup current configuration
sudo cp -r /etc/samba /etc/samba.backup.$(date +%Y%m%d)

# Extract new release
tar -xzf samba-manager-1.2.0.tar.gz
cd samba-manager-1.2.0

# Install
sudo ./install.sh

# Restart service
sudo systemctl restart samba-manager
```

## Reporting Issues

Found a problem with a release? Report it:
- **GitHub Issues**: https://github.com/lyarinet/Samba-Manager/issues
- **Security Issues**: Contact maintainers privately

## License

All releases are distributed under the MIT License. See LICENSE file in package.

## Support

- **Documentation**: https://github.com/lyarinet/Samba-Manager/wiki
- **FAQ**: See TROUBLESHOOTING.md in the release package
- **Community**: GitHub Discussions (coming soon)
