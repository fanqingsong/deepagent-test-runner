-- Migration to fix created_by column type mismatch
-- Change created_by from VARCHAR to INTEGER to store user IDs instead of usernames

BEGIN;

-- Step 1: Add a temporary column to hold integer user IDs
ALTER TABLE test_definitions
    ADD COLUMN IF NOT EXISTS created_by_id INTEGER DEFAULT 1;

-- Step 2: Migrate data - if created_by is 'system', set to 1 (admin user)
-- Otherwise, we'd need to look up usernames in users table, but for now default to admin
UPDATE test_definitions
SET created_by_id = CASE
    WHEN created_by = 'system' THEN 1
    WHEN created_by ~ '^[0-9]+$' THEN CAST(created_by AS INTEGER)
    ELSE 1  -- Default to admin user for any non-numeric values
END;

-- Step 3: Drop the old created_by column and rename the new one
ALTER TABLE test_definitions
    DROP COLUMN IF EXISTS created_by;

ALTER TABLE test_definitions
    RENAME COLUMN created_by_id TO created_by;

-- Step 4: Set NOT NULL and default
ALTER TABLE test_definitions
    ALTER COLUMN created_by SET NOT NULL;

ALTER TABLE test_definitions
    ALTER COLUMN created_by SET DEFAULT 1;

COMMIT;

-- Verify the migration
SELECT 'Migration completed successfully!' AS status;
