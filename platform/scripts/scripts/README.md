# Scripts

This directory contains utility scripts for the unified backend service.

## init_rbac.py

Initialize the RBAC (Role-Based Access Control) system with default roles and permissions.

### Usage

Run from the project root directory:

```bash
cd docker-compose
docker exec -it cc-test-unified-backend python app/scripts/init_rbac.py
```

Or run locally (requires database connection):

```bash
cd unified-backend-service/app/scripts
python init_rbac.py
```

### What it creates

**Permissions:**
- User management: `create:user`, `read:user`, `update:user`, `delete:user`
- Test management: `create:test`, `read:test`, `update:test`, `delete:test`, `execute:test`
- Schedule management: `create:schedule`, `read:schedule`, `update:schedule`, `delete:schedule`
- Role management: `create:role`, `read:role`, `update:role`, `delete:role`

**Roles:**
- **admin** - All permissions (system role)
- **tester** - Test and schedule management permissions
- **viewer** - Read-only permissions

### Notes

- The script is idempotent - it won't create duplicates if run multiple times
- System roles (like admin) are marked with `is_system=True` and cannot be deleted through the API
