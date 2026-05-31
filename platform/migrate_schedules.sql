-- Migration: Add missing fields to schedules table
-- Run this to update the database schema for advanced scheduling features

-- Add missing columns
ALTER TABLE schedules
ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(20) DEFAULT 'individual' NOT NULL,
ADD COLUMN IF NOT EXISTS test_definition_id INTEGER,
ADD COLUMN IF NOT EXISTS test_suite_id INTEGER,
ADD COLUMN IF NOT EXISTS tag_filter VARCHAR(100),
ADD COLUMN IF NOT EXISTS preset_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC' NOT NULL,
ADD COLUMN IF NOT EXISTS environment_overrides JSONB DEFAULT '{}'::jsonb NOT NULL,
ADD COLUMN IF NOT EXISTS allow_concurrent BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS retry_interval_seconds INTEGER DEFAULT 60 NOT NULL,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Add foreign key constraints
ALTER TABLE schedules
ADD CONSTRAINT IF NOT EXISTS fk_schedules_test_definition_id
FOREIGN KEY (test_definition_id) REFERENCES test_definitions(id) ON DELETE SET NULL;

ALTER TABLE schedules
ADD CONSTRAINT IF NOT EXISTS fk_schedules_test_suite_id
FOREIGN KEY (test_suite_id) REFERENCES test_suites(id) ON DELETE SET NULL;

-- Drop old environment column if exists (replaced by environment_overrides)
ALTER TABLE schedules
DROP COLUMN IF EXISTS environment;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_schedules_schedule_type
ON schedules(schedule_type);

CREATE INDEX IF NOT EXISTS idx_schedules_test_definition_id
ON schedules(test_definition_id)
WHERE test_definition_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_schedules_test_suite_id
ON schedules(test_suite_id)
WHERE test_suite_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_schedules_created_by
ON schedules(created_by);

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'schedules'
AND column_name IN (
    'schedule_type',
    'test_definition_id',
    'test_suite_id',
    'tag_filter',
    'preset_type',
    'timezone',
    'environment_overrides',
    'allow_concurrent',
    'max_retries',
    'retry_interval_seconds',
    'updated_at'
)
ORDER BY ordinal_position;
