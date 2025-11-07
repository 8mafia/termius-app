# ParSSH - Termius-like Multi-Platform SSH Manager

A complete, production-grade SSH manager and client that reproduces the full functionality of Termius across multiple platforms: Web (Next.js), Windows (Electron), Android (Kotlin), and PWA.

## Features

- **Multi-platform Support**: Web (Next.js), Windows (Electron), Android (Kotlin), PWA
- **Real-time Terminal Access**: WebSocket-based terminal with xterm.js
- **SSH Gateway**: High-performance Go SSH proxy with session management
- **Encrypted Credential Storage**: Per-user encryption with cross-device sync
- **Multi-user Session Sharing**: Collaborative terminal sessions
- **One-click Deployment**: Automated Docker deployment with SSL support
- **Modern Authentication**: JWT + OAuth2 (Google/GitHub) with 2FA support
- **SFTP File Management**: Built-in file browser and transfer
- **Port Forwarding**: Local and remote port forwarding management
- **Security First**: OWASP compliant, encryption at rest, rate limiting

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Linux server (Ubuntu 22.04 or AlmaLinux 9)
- Domain name (optional, for HTTPS)

### One-Click Deployment

```bash
# Clone the repository
git clone https://github.com/your-org/parssh.git
cd parssh

# Run the one-click deployment script
chmod +x oneclick.sh
./oneclick.sh
```

The script will:
- Detect your OS and install Docker
- Generate secure secrets
- Ask if you want HTTPS (with automatic SSL certificate)
- Deploy all services
- Create an admin user

### Manual Deployment

```bash
# Copy environment template
cp .env.example .env

# Edit the environment file with your settings
nano .env

# Start all services
docker-compose up -d --build

# Initialize the database
docker-compose exec api alembic upgrade head

# Create admin user
docker-compose exec api python scripts/seed-admin.py
```

## Access Information

After deployment:

- **Web Application**: http://localhost (or https://your-domain.com)
- **API Documentation**: http://localhost/docs
- **Default Admin**: admin@parssh.local / Admin123!

⚠️ **Important**: Change the default admin password on first login!

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Mobile App    │    │  Desktop App    │
│   (Next.js)     │    │   (Kotlin)      │    │   (Electron)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │       Nginx Reverse       │
                    │        Proxy              │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
┌─────────▼───────┐    ┌─────────▼───────┐    ┌─────────▼───────┐
│   FastAPI       │    │   SSH Gateway   │    │   Next.js       │
│   Backend       │    │   (Go)          │    │   Frontend      │
│   (Port 8000)   │    │   (Port 8080)   │    │   (Port 3000)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────────────┘
          │                      │
          └──────────┬───────────┘
                     │
          ┌──────────▼──────────┐
          │   PostgreSQL DB     │
          │   (Port 5432)       │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │      Redis          │
          │   (Port 6379)       │
          └─────────────────────┘
```

## Services

### API (FastAPI Backend)
- REST API with auto-generated OpenAPI docs
- JWT authentication with refresh tokens
- PostgreSQL database with SQLAlchemy ORM
- Redis for caching and session management
- Comprehensive security measures

### SSH Gateway (Go)
- High-performance SSH connection management
- WebSocket terminal proxy with real-time collaboration
- SFTP file operations
- Connection pooling and session management
- Multi-user session sharing

### Web Frontend (Next.js)
- Modern React 18 with TypeScript
- xterm.js terminal emulation
- Real-time WebSocket connections
- PWA-ready with offline support
- Responsive design with Tailwind CSS

### Mobile App (Kotlin)
- Native Android app with Jetpack Compose
- SSH client integration
- Encrypted data synchronization
- SFTP file browser

### Desktop App (Electron)
- Cross-platform desktop application
- Native web view wrapper
- System integration features

## Security

- **Encryption**: AES-256-GCM encryption for all credentials
- **Authentication**: JWT with Argon2 password hashing
- **Rate Limiting**: Configurable limits on sensitive endpoints
- **HTTPS**: Automatic SSL certificate generation with Let's Encrypt
- **Audit Logging**: Comprehensive security event logging
- **CORS/CSRF**: Proper cross-origin request protection

## Development

### Local Development

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# Run backend tests
cd api && pytest

# Run frontend tests
cd web && npm test

# Run SSH gateway tests
cd ssh-gateway && go test ./...
```

### Project Structure

```
parssh/
├── api/                 # FastAPI backend
├── web/                 # Next.js frontend
├── ssh-gateway/         # Go SSH gateway
├── nginx/               # Nginx configuration
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── android/             # Android app
├── electron/            # Electron desktop app
├── ci/                  # CI/CD configs
├── docker-compose.yml   # Production deployment
├── oneclick.sh          # One-click deployment
└── README.md           # This file
```

## API Documentation

Once deployed, visit `/docs` for interactive API documentation.

## Testing

```bash
# Run all tests
./scripts/test-all.sh

# Run smoke tests
./scripts/smoke-test.sh

# Run integration tests
./scripts/integration-test.sh
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Documentation](docs/)
- 🐛 [Issue Tracker](https://github.com/your-org/parssh/issues)
- 💬 [Discussions](https://github.com/your-org/parssh/discussions)

## Acknowledgments

- Inspired by Termius - the excellent cross-platform SSH client
- Built with modern open-source technologies
- Community-driven development
