# Frontend Directory Cleanup

## Issue Found

The frontend directory structure contains some incorrectly placed files/directories:

1. **`src/node_modules/` (263MB)**: This directory should not exist in the source tree
   - `node_modules` should only exist inside the Docker container at `/app/frontend/node_modules`
   - The Docker volume mount makes this directory persistent and causes permission issues
   - Already properly ignored by `.gitignore`

2. **`src/dist/` (1.3MB)**: Build artifacts that should not be in source control
   - Created by `npm run build` during development
   - Already properly ignored by `.gitignore`

## Proper Directory Structure

```
platform/frontend/
├── src/                          # Source files (mounted to container)
│   ├── package.json             # Dependencies for frontend
│   ├── package-lock.json        # Lock file for dependencies
│   ├── vite.config.js           # Vite configuration
│   ├── main.jsx                 # Entry point
│   ├── App.jsx                  # Main component
│   ├── components/              # React components
│   ├── pages/                   # Page components
│   ├── services/                # API services
│   ├── api/                     # API utilities
│   ├── contexts/                # React contexts
│   ├── hooks/                   # Custom hooks
│   ├── locales/                 # i18n translations
│   ├── index.html               # HTML template
│   ├── index.css                # Global styles
│   └── .gitignore              # Excludes node_modules/ and dist/
├── Dockerfile                    # Container build instructions
├── docker-entrypoint-dev.sh     # Development entrypoint
└── README.md                     # This file
```

## Inside Docker Container

```
/app/frontend/                   # Working directory in container
├── node_modules/                # Installed by npm install in container
│   └── (dependencies)           # Managed by Docker volume
├── dist/                        # Build output (only in production builds)
│   └── (built assets)           # Created during docker build
└── (all source files from src/) # Mounted from host
```

## Docker Volume Architecture

The Docker setup uses a sophisticated volume strategy:

1. **Source Mount**: `./frontend/src:/app/frontend` (bind mount)
   - Provides hot-reload during development
   - Changes on host immediately reflected in container

2. **node_modules Volume**: Anonymous Docker volume for `/app/frontend/node_modules`
   - Prevents host node_modules from conflicting with container
   - Allows cross-platform development (Windows/Mac/Linux)
   - Managed by `docker-entrypoint-dev.sh` smart installation

3. **Smart Installation**: The entrypoint script automatically:
   - Detects when `package-lock.json` changes
   - Reinstalls dependencies when needed
   - Preserves node_modules across container restarts

## Cleanup Instructions

Due to Docker volume permissions, manual cleanup requires elevated access:

### Option 1: Using Docker (Recommended)
```bash
# Stop and remove the frontend container
docker compose stop frontend
docker compose rm -f frontend

# Manually clean up (may require sudo for some files)
sudo rm -rf frontend/src/node_modules
sudo rm -rf frontend/src/dist

# Restart the environment
docker compose up -d frontend
```

### Option 2: Using the Cleanup Script
```bash
# Run the pre-created cleanup script with sudo
sudo bash /tmp/cleanup-frontend.sh
```

### Option 3: Leave As-Is (Acceptable)
Since both `node_modules/` and `dist/` are already in `.gitignore`, they won't be committed to git. The Docker setup is designed to handle this structure correctly.

## Why This Structure Works

1. **Cross-Platform Compatibility**: Docker node_modules volume prevents OS-specific binary conflicts
2. **Hot-Reload Development**: Source files are bind-mounted for instant updates
3. **Smart Dependency Management**: Entrypoint script handles installation automatically
4. **Clean Separation**: Build artifacts and dependencies stay in container, not in source

## Verification

After cleanup, verify the structure:

```bash
# Check frontend source size (should be ~5MB without node_modules)
du -sh platform/frontend/src/

# Check git status (node_modules and dist should not appear)
git status platform/frontend/src/

# Verify Docker setup works
docker compose up -d frontend
docker logs deepagent-tester-frontend
```

## Maintenance

To prevent future issues:

1. **Never run `npm install` in the `src/` directory** on the host
2. **Always use Docker** for frontend development and building
3. **Commit source files only** - node_modules and dist are already ignored
4. **Trust the Docker entrypoint** to handle dependency installation

The Docker setup is designed to manage node_modules properly. Let it do its job!
