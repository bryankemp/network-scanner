# Container Registry Guide

This document explains how to use Network Scanner with container registries, specifically GitHub Container Registry (GHCR).

## Table of Contents

- [Quick Start](#quick-start)
- [Using Pre-built Images](#using-pre-built-images)
- [Building and Publishing](#building-and-publishing)
- [Authentication](#authentication)
- [Available Tags](#available-tags)
- [Multi-Architecture Support](#multi-architecture-support)

## Quick Start

### Pull and Run from GHCR

```bash
# Pull the latest image
docker pull ghcr.io/bryank/network-scan:latest

# Create data directories
mkdir -p data/scan_outputs data/database

# Run the container
docker run -d \
  --name network-scan \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -p 8000:8000 \
  -p 8001:8001 \
  -v $(pwd)/data/scan_outputs:/app/scan_outputs \
  -v $(pwd)/data/database:/app/database \
  ghcr.io/bryank/network-scan:latest
```

Access the application at:
- **Web UI/API**: `http://localhost:8000`
- **MCP Server**: `http://localhost:8001`

### Using docker-compose

```bash
# Use the pre-configured GHCR compose file
docker-compose -f docker-compose.ghcr.yml up -d

# Check status
docker-compose -f docker-compose.ghcr.yml ps

# View logs
docker-compose -f docker-compose.ghcr.yml logs -f
```

## Using Pre-built Images

### Available Images

All images are hosted on GitHub Container Registry:

```
ghcr.io/bryank/network-scan:latest       # Latest stable release
ghcr.io/bryank/network-scan:main         # Latest from main branch
ghcr.io/bryank/network-scan:v1.0.0       # Specific version tag
```

### Pulling Images

```bash
# Latest stable release
docker pull ghcr.io/bryank/network-scan:latest

# Specific version
docker pull ghcr.io/bryank/network-scan:v1.0.0

# Development version
docker pull ghcr.io/bryank/network-scan:main
```

### Running Containers

**Basic run:**

```bash
docker run -d \
  --name network-scan \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -p 8000:8000 \
  -p 8001:8001 \
  ghcr.io/bryank/network-scan:latest
```

**With persistent storage:**

```bash
docker run -d \
  --name network-scan \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -p 8000:8000 \
  -p 8001:8001 \
  -v network-scan-db:/app/database \
  -v network-scan-outputs:/app/scan_outputs \
  ghcr.io/bryank/network-scan:latest
```

**With custom timezone:**

```bash
docker run -d \
  --name network-scan \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -p 8000:8000 \
  -p 8001:8001 \
  -e TZ=America/New_York \
  ghcr.io/bryank/network-scan:latest
```

## Building and Publishing

### Manual Build and Push

```bash
# Build the image
docker build -f Dockerfile.production -t ghcr.io/bryank/network-scan:latest .

# Tag with version
docker tag ghcr.io/bryank/network-scan:latest ghcr.io/bryank/network-scan:v1.0.0

# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u bryank --password-stdin

# Push images
docker push ghcr.io/bryank/network-scan:latest
docker push ghcr.io/bryank/network-scan:v1.0.0
```

### Automated with GitHub Actions

The repository includes a GitHub Actions workflow that automatically builds and publishes images:

**Triggers:**
- **Push to main branch** → `ghcr.io/bryank/network-scan:main` and `ghcr.io/bryank/network-scan:latest`
- **Version tag (v*)** → `ghcr.io/bryank/network-scan:v1.0.0` and semantic versions
- **Manual trigger** → Via GitHub Actions UI

**To publish a new version:**

```bash
# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0

# GitHub Actions will automatically build and publish:
# - ghcr.io/bryank/network-scan:v1.0.0
# - ghcr.io/bryank/network-scan:1.0
# - ghcr.io/bryank/network-scan:1
# - ghcr.io/bryank/network-scan:latest
```

### Multi-Architecture Builds

The GitHub Actions workflow builds for multiple architectures:
- **linux/amd64** - Intel/AMD 64-bit (most common)
- **linux/arm64** - ARM 64-bit (Apple Silicon, Raspberry Pi 4+)

Docker will automatically pull the correct architecture for your platform.

## Authentication

### Public Access

By default, images are public and don't require authentication:

```bash
docker pull ghcr.io/bryank/network-scan:latest
```

### Private Registry Authentication

If the repository is private or you hit rate limits:

```bash
# Create a GitHub Personal Access Token with 'read:packages' scope
# https://github.com/settings/tokens

# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Now you can pull
docker pull ghcr.io/bryank/network-scan:latest
```

### Persisting Credentials

Docker stores credentials in `~/.docker/config.json` after login, so you only need to login once.

### Using in CI/CD

**GitHub Actions:**

```yaml
- name: Login to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
```

**GitLab CI:**

```yaml
docker_pull:
  script:
    - echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
    - docker pull ghcr.io/bryank/network-scan:latest
```

## Available Tags

### Tag Strategy

| Tag Pattern | Description | Example |
|-------------|-------------|---------|
| `latest` | Most recent stable release | `ghcr.io/bryank/network-scan:latest` |
| `main` | Latest from main branch | `ghcr.io/bryank/network-scan:main` |
| `v*` | Full semantic version | `ghcr.io/bryank/network-scan:v1.0.0` |
| `major.minor` | Minor version | `ghcr.io/bryank/network-scan:1.0` |
| `major` | Major version | `ghcr.io/bryank/network-scan:1` |

### Choosing a Tag

**For production:**
- Use specific version tags (e.g., `v1.0.0`) for reproducible deployments
- Or use minor version tags (e.g., `1.0`) for automatic patch updates

**For development:**
- Use `main` tag to test latest changes
- Use `latest` for the most recent stable release

**For testing:**
- Use specific PR or branch tags if available

## Multi-Architecture Support

### Verifying Architecture

```bash
# Inspect image to see available architectures
docker buildx imagetools inspect ghcr.io/bryank/network-scan:latest

# Output shows platforms:
# - linux/amd64
# - linux/arm64
```

### Platform-Specific Pulls

Docker automatically selects the correct platform, but you can specify explicitly:

```bash
# Force AMD64
docker pull --platform linux/amd64 ghcr.io/bryank/network-scan:latest

# Force ARM64
docker pull --platform linux/arm64 ghcr.io/bryank/network-scan:latest
```

### Building Multi-Architecture Locally

```bash
# Set up buildx
docker buildx create --use

# Build for multiple platforms
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -f Dockerfile.production \
  -t ghcr.io/bryank/network-scan:latest \
  --push \
  .
```

## Troubleshooting

### Image Pull Failures

**Rate limiting:**
```bash
# Authenticate to increase rate limits
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

**Network issues:**
```bash
# Retry with explicit timeout
docker pull --timeout 300s ghcr.io/bryank/network-scan:latest
```

**Architecture mismatch:**
```bash
# Verify your platform
docker version | grep -i platform

# Pull specific architecture
docker pull --platform linux/amd64 ghcr.io/bryank/network-scan:latest
```

### Container Runtime Issues

**Permission denied for nmap:**
```bash
# Ensure capabilities are set
docker run --cap-add NET_RAW --cap-add NET_ADMIN ...
```

**Cannot bind to port:**
```bash
# Check if port is in use
lsof -i :8000

# Use different port
docker run -p 9000:8000 ...
```

### Image Size Issues

The production image is optimized but still substantial due to nmap and Flutter dependencies:

```bash
# Check image size
docker images ghcr.io/bryank/network-scan:latest

# Clean up old images
docker image prune -a
```

## Best Practices

### Security

1. **Always specify a version tag in production** - avoid `latest`
2. **Use read-only tokens** for pulling images
3. **Scan images for vulnerabilities:**
   ```bash
   docker scan ghcr.io/bryank/network-scan:latest
   ```

### Performance

1. **Use volume mounts** for persistent data
2. **Set resource limits** in production:
   ```bash
   docker run --memory=2g --cpus=2 ...
   ```
3. **Enable BuildKit** for faster builds:
   ```bash
   export DOCKER_BUILDKIT=1
   ```

### Monitoring

1. **Check container health:**
   ```bash
   docker inspect --format='{{.State.Health.Status}}' network-scan
   ```

2. **View logs:**
   ```bash
   docker logs -f network-scan
   ```

3. **Monitor resource usage:**
   ```bash
   docker stats network-scan
   ```

## Additional Resources

- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Dockerfile Best Practices](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

**Author:** Bryan Kemp <bryan@kempville.com>  
**License:** BSD 3-Clause
