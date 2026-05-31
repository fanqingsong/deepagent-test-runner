-- Migration script to update schedules table schema for unified backend
-- This adds the columns needed by the new unified-backend-service

BEGIN;

-- Step 1: Add new columns to schedules table (one at a time to avoid conflicts)
ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS schedule_type VARCHAR(20) DEFAULT 'single';

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS test_definition_id INTEGER;

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS test_suite_id INTEGER;

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS tag_filter VARCHAR(255);

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS preset_type VARCHAR(50);

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS timezone VARCHAR(50) DEFAULT 'UTC';

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS environment_overrides JSONB DEFAULT '{}'::jsonb;

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS allow_concurrent BOOLEAN DEFAULT FALSE;

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 0;

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS retry_interval_seconds INTEGER DEFAULT 60;

ALTER TABLE schedules
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Step 2: Migrate data from old test_definition_ids array to new structure
UPDATE schedules
SET
    schedule_type = CASE
        WHEN array_length(test_definition_ids, 1) = 1 THEN 'single'
        ELSE 'suite'
    END,
    test_definition_id = CASE
        WHEN array_length(test_definition_ids, 1) = 1 THEN test_definition_ids[1]
        ELSE NULL
    END::INTEGER,
    test_suite_id = CASE
        WHEN array_length(test_definition_ids, 1) > 1 THEN NULL::INTEGER
        ELSE NULL::INTEGER
    END;

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedules_schedule_type ON schedules(schedule_type);
CREATE INDEX IF NOT EXISTS idx_schedules_test_definition_id ON schedules(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_schedules_test_suite_id ON schedules(test_suite_id);

COMMIT;

-- Verify the migration
SELECT 'Migration completed successfully!' AS status;
