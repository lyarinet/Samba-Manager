"""
Version management for Samba Manager
"""

__version__ = "1.3.0"
__author__ = "Lyarinet"
__license__ = "MIT"
__description__ = "Web-based interface for managing Samba file sharing on Linux systems"

# Version history
VERSION_HISTORY = {
    "1.0.0": {
        "date": "2024-01-15",
        "description": "Initial release with core functionality",
        "features": [
            "Web-based Samba administration interface",
            "Share management (create, edit, delete)",
            "User and group management",
            "Global settings configuration",
            "Service control and monitoring",
        ],
    },
    "1.1.0": {
        "date": "2024-06-20",
        "description": "Added terminal access and improved security",
        "features": [
            "Terminal access via GoTTY",
            "Enhanced CSRF protection",
            "Rate limiting for login attempts",
            "Improved input validation",
            "Security hardening",
        ],
    },
    "1.2.0": {
        "date": "2026-01-23",
        "description": "Added comprehensive release pack and distribution tools",
        "features": [
            "Release pack generation",
            "Docker image support",
            "Checksums and verification",
            "Distribution archives (tar.gz, zip, deb)",
            "Installation verification script",
        ],
    },
    "1.3.0": {
        "date": "2026-01-24",
        "description": "Enhanced Docker support and Kubernetes preparation",
        "features": [
            "Improved Docker image with optimizations",
            "Docker Compose enhancements",
            "Health check improvements",
            "Kubernetes manifests (beta)",
            "Advanced monitoring capabilities",
        ],
    },
}


def get_version():
    """Get current version string"""
    return __version__


def get_version_info():
    """Get full version information"""
    return {
        "version": __version__,
        "author": __author__,
        "license": __license__,
        "description": __description__,
        "latest_release": VERSION_HISTORY.get(__version__, {}),
    }
