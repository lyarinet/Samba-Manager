# Samba Manager - Release Pack Documentation

This directory contains comprehensive release management tools and documentation for Samba Manager.

## Quick Start

### Build a Release
```bash
chmod +x build_release.sh
./build_release.sh
```

### Validate Release
```bash
chmod +x validate_release.sh
./validate_release.sh
```

### Publish Release
```bash
chmod +x publish_release.sh
./publish_release.sh
```

## Files and Directories

### Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| [build_release.sh](../build_release.sh) | Build release packages | `./build_release.sh` |
| [validate_release.sh](../validate_release.sh) | Validate release integrity | `./validate_release.sh` |
| [publish_release.sh](../publish_release.sh) | Publish to GitHub | `./publish_release.sh` |
| [generate_changelog.sh](../generate_changelog.sh) | Generate changelog | `./generate_changelog.sh` |

### Documentation

| File | Purpose |
|------|---------|
| [RELEASE_WORKFLOW.md](../RELEASE_WORKFLOW.md) | Complete release process guide |
| [releases/README.md](./README.md) | Distribution and installation guide |
| [version.py](../version.py) | Version information and history |

### Directories

| Directory | Contents |
|-----------|----------|
| `stable/` | Current stable release packages |
| `beta/` | Beta and RC releases (optional) |
| `archive/` | Previous stable releases |
| `docker/` | Docker configuration and build files |
| `signatures/` | GPG signatures (optional) |

### Docker Files

| File | Purpose |
|------|---------|
| `docker/Dockerfile` | Container image definition |
| `docker/docker-compose.yml` | Multi-service composition |
| `docker/supervisord.conf` | Service supervision |
| `docker/entrypoint.sh` | Container startup script |

**Docker Hub**: https://hub.docker.com/r/lyarinet/samba-manager

## Release Formats

### Source Distribution (tar.gz / zip)
- Complete application source code
- Python requirements file
- Installation scripts
- Documentation
- Configuration templates

### Docker Image
- Pre-configured container (available on Docker Hub)
- All dependencies included
- Ready-to-deploy
- Supports docker-compose
- **Pull**: `docker pull lyarinet/samba-manager:latest`

## Installation Methods

1. **One-Line Install**: `curl | sudo bash`
2. **Manual Install**: Extract and run install.sh
3. **Docker (Docker Hub)**: `docker run -p 5000:5000 lyarinet/samba-manager:1.3.0`
4. **Docker (Local Build)**: `cd releases/docker && docker-compose up`
5. **Package Manager**: `.deb` files (future)

**Docker Hub Repository**: https://hub.docker.com/r/lyarinet/samba-manager

## Release Checklist

- [ ] Update version in `version.py`
- [ ] Update RELEASE_NOTES.md
- [ ] Run `./build_release.sh`
- [ ] Run `./validate_release.sh`
- [ ] Test installation
- [ ] Commit and tag in git
- [ ] Run `./publish_release.sh`
- [ ] Update documentation
- [ ] Announce release

## Verification

Verify downloaded packages:
```bash
sha256sum -c releases/stable/checksums.txt
```

All files should show "OK".

## Support

- **Documentation**: See RELEASE_WORKFLOW.md
- **Issues**: GitHub Issues
- **Questions**: GitHub Discussions

## License

All release materials are distributed under the MIT License.
