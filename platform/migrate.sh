#!/bin/bash

# SQLite to PostgreSQL Migration Script
# This script automates the migration process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "SQLite to PostgreSQL Migration"
echo "======================================"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create a .env file with your PostgreSQL credentials"
    exit 1
fi

# Load environment variables
source .env

# Check required variables
if [ -z "$POSTGRES_PASSWORD" ]; then
    echo -e "${RED}Error: POSTGRES_PASSWORD not set in .env${NC}"
    exit 1
fi

# Check if SQLite database exists
SQLITE_DB="../claude_code_tests.db"
if [ ! -f "$SQLITE_DB" ]; then
    echo -e "${YELLOW}Warning: SQLite database not found at $SQLITE_DB${NC}"
    echo "Continuing anyway (this is normal for fresh installations)..."
fi

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if ! docker exec cc-test-postgres pg_isready -U cc_test_user -d claude_code_tests > /dev/null 2>&1; then
    echo -e "${RED}Error: PostgreSQL is not running${NC}"
    echo "Please start PostgreSQL first: docker-compose up -d postgres"
    exit 1
fi

echo -e "${GREEN}✓ PostgreSQL is running${NC}"
echo ""

# Prompt for dry run
echo -e "${YELLOW}Do you want to run a dry-run first? (recommended)${NC}"
read -p "Run dry-run? (y/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Running dry-run migration..."
    python scripts/migrate_sqlite_to_postgres.py \
        --sqlite-path "$SQLITE_DB" \
        --postgres-host localhost \
        --postgres-port 5432 \
        --postgres-db "${POSTGRES_DB:-claude_code_tests}" \
        --postgres-user "${POSTGRES_USER:-cc_test_user}" \
        --postgres-password "$POSTGRES_PASSWORD" \
        --dry-run

    echo ""
    echo -e "${GREEN}Dry-run completed successfully${NC}"
    echo ""
    echo "Please review the output above and confirm you want to proceed."
    read -p "Continue with actual migration? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled"
        exit 0
    fi
fi

# Run actual migration
echo ""
echo "Running migration..."
echo "This may take a few minutes depending on data size..."
echo ""

python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path "$SQLITE_DB" \
    --postgres-host localhost \
    --postgres-port 5432 \
    --postgres-db "${POSTGRES_DB:-claude_code_tests}" \
    --postgres-user "${POSTGRES_USER:-cc_test_user}" \
    --postgres-password "$POSTGRES_PASSWORD"

echo ""
echo -e "${GREEN}======================================"
echo "Migration completed successfully!"
echo "======================================${NC}"
echo ""
echo "Next steps:"
echo "1. Start all services: docker-compose up -d"
echo "2. Check dashboard: http://localhost:8003"
echo "3. Review API docs: http://localhost:8001/api/docs"
echo ""
echo "For more information, see MIGRATION_GUIDE.md"
