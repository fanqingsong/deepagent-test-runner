-- Migration: Add AI planning fields to test_definitions table
-- Run this to update the database schema

-- Add AI planning columns
ALTER TABLE test_definitions
ADD COLUMN IF NOT EXISTS test_goal TEXT,
ADD COLUMN IF NOT EXISTS test_context JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS plan_generation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS ai_generated_plan JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS plan_metadata JSONB DEFAULT '{}'::jsonb;

-- Fix created_by column type (VARCHAR -> INTEGER FK)
-- Step 1: Create temporary column
ALTER TABLE test_definitions
ADD COLUMN IF NOT EXISTS created_by_new INTEGER;

-- Step 2: Migrate data (convert 'system' to NULL, otherwise try to parse as integer)
UPDATE test_definitions
SET created_by_new = CASE
    WHEN created_by = 'system' OR created_by ~ '^[0-9]+$' THEN NULL
    ELSE NULL::INTEGER
END;

-- Step 3: Drop old column and rename new one
ALTER TABLE test_definitions
DROP COLUMN IF EXISTS created_by;

ALTER TABLE test_definitions
RENAME COLUMN created_by_new TO created_by;

-- Add foreign key constraint
ALTER TABLE test_definitions
ADD CONSTRAINT fk_test_definitions_created_by
FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_test_definitions_plan_status
ON test_definitions(plan_generation_status)
WHERE plan_generation_status IN ('pending', 'generated', 'approved');

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'test_definitions'
AND column_name IN ('test_goal', 'test_context', 'plan_generation_status', 'ai_generated_plan', 'plan_metadata', 'created_by')
ORDER BY ordinal_position;
