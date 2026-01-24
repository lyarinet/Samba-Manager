#!/bin/bash
#
# Build Docker image for Samba Manager
# This script must be run from the project root directory
#

set -e

VERSION=$(python3 -c "from version import __version__; print(__version__)")
IMAGE_NAME="samba-manager"
IMAGE_TAG="${1:-$VERSION}"

echo "Building Docker image: $IMAGE_NAME:$IMAGE_TAG"
echo ""

# Build from the project root with the docker directory as context
docker build \
    -f releases/docker/Dockerfile \
    -t "$IMAGE_NAME:$IMAGE_TAG" \
    -t "$IMAGE_NAME:latest" \
    releases/docker

echo ""
echo "✓ Docker image built successfully!"
echo "  Image: $IMAGE_NAME:$IMAGE_TAG"
echo "  Latest tag: $IMAGE_NAME:latest"
echo ""
echo "To run the container:"
echo "  docker-compose -f releases/docker/docker-compose.yml up"
echo ""
echo "Or manually:"
echo "  docker run -p 5000:5000 $IMAGE_NAME:$IMAGE_TAG"
