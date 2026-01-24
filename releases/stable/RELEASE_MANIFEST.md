# Samba Manager 1.3.0 Release Manifest

**Release Date**: Sat Jan 24 05:52:47 UTC 2026
**Build System**: Linux
**Release Manager**: Release Pack Builder Script

## Package Contents

### Archives
- **samba-manager-1.3.0.tar.gz** (GNU tar + gzip)
  - Size: 180K
  - SHA256: 6055d5a38cbad50da734a328503f726a436fccffeedcab057ab814ba66327eb7

- **samba-manager-1.3.0.zip** (ZIP format)
  - Size: 200K
  - SHA256: 1b32cf319b2889747c4a7731c4ffc9f49479c1b127dae80eb2b72b45e87b67b8

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
   ```bash
   tar -xzf samba-manager-1.3.0.tar.gz
   cd samba-manager-1.3.0
   sudo ./install.sh
   ```

2. **Docker Deployment**
   ```bash
   cd samba-manager-1.3.0
   docker build -t samba-manager:1.3.0 .
   docker run -p 5000:5000 -v /etc/samba:/etc/samba samba-manager:1.3.0
   ```

## Checksum Verification

Verify package integrity before installation:

```bash
sha256sum -c checksums.txt
```

Expected output:
```
samba-manager-1.3.0.tar.gz: OK
samba-manager-1.3.0.zip: OK
```

## Quick Start

After installation:

1. Start the service:
   ```bash
   sudo systemctl start samba-manager
   ```

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
Build Date: 2026-01-24 05:52:47

