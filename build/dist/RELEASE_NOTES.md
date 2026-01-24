# Samba Manager v1.3.0 Release Notes

**Release Date**: 2026-01-24

## Overview

This release of Samba Manager includes all features and improvements up to version 1.3.0.

## What's Included

This release package includes:
- Complete Samba Manager web application
- Installation scripts for multiple distributions
- Docker configuration for containerized deployment
- Comprehensive documentation
- Configuration templates

## Installation

### Quick Start
```bash
# Extract the package
tar -xzf samba-manager-1.3.0.tar.gz
cd samba-manager-1.3.0

# Run the installation
sudo ./install.sh
```

### Docker Deployment
```bash
docker build -t samba-manager:1.3.0 .
docker run -p 5000:5000 -v /etc/samba:/etc/samba samba-manager:1.3.0
```

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

```bash
sha256sum -c checksums.txt
```

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
   ```bash
   sudo cp -r /etc/samba /etc/samba.backup.$(date +%Y%m%d)
   ```

2. Extract and install the new version:
   ```bash
   tar -xzf samba-manager-1.3.0.tar.gz
   cd samba-manager-1.3.0
   sudo ./install.sh
   ```

3. Restart the service:
   ```bash
   sudo systemctl restart samba-manager
   ```

## Support

- **Issues**: https://github.com/lyarinet/Samba-Manager/issues
- **Discussions**: https://github.com/lyarinet/Samba-Manager/discussions
- **Documentation**: https://github.com/lyarinet/Samba-Manager/wiki

## License

This software is released under the MIT License. See the LICENSE file for details.

## Contributors

- Lyarinet - Project founder and maintainer

---

**Download**: https://github.com/lyarinet/Samba-Manager/releases/tag/v1.3.0

