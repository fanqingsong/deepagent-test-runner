-- Migration: Add AI planning fields to test_steps table
-- Run this to update the database schema

-- Add AI planning columns
ALTER TABLE test_steps
ADD COLUMN IF NOT EXISTS is_ai_generated BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
ADD COLUMN IF NOT EXISTS parent_step_id INTEGER;

-- Add foreign key for parent_step_id
ALTER TABLE test_steps
ADD CONSTRAINT IF NOT EXISTS fk_test_steps_parent_step
FOREIGN KEY (parent_step_id) REFERENCES test_steps(id) ON DELETE SET NULL;

-- Add index for parent_step_id
CREATE INDEX IF NOT EXISTS idx_test_steps_parent_step_id
ON test_steps(parent_step_id);

-- Verify migration
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'test_steps'
AND column_name IN ('is_ai_generated', 'confidence_score', 'parent_step_id')
ORDER BY ordinal_position;
