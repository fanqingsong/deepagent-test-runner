-- Migration Script: Add AI Planning Fields
-- Version: 001
-- Date: 2025-01-16
-- Description: Add fields for AI-powered test planning and adaptive execution

-- Start transaction
BEGIN;

-- ============================================
-- Add AI Planning Fields to test_definitions table
-- ============================================

ALTER TABLE test_definitions
ADD COLUMN IF NOT EXISTS test_goal TEXT,
ADD COLUMN IF NOT EXISTS test_context JSONB DEFAULT '{}' NOT NULL,
ADD COLUMN IF NOT EXISTS plan_generation_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
ADD COLUMN IF NOT EXISTS ai_generated_plan JSONB DEFAULT '{}' NOT NULL,
ADD COLUMN IF NOT EXISTS plan_metadata JSONB DEFAULT '{}' NOT NULL;

-- Add index for plan generation status
CREATE INDEX IF NOT EXISTS idx_test_definitions_plan_status ON test_definitions(plan_generation_status);

-- ============================================
-- Add AI Tracking Fields to test_steps table
-- ============================================

ALTER TABLE test_steps
ADD COLUMN IF NOT EXISTS is_ai_generated BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS confidence_score FLOAT,
ADD COLUMN IF NOT EXISTS parent_step_id INTEGER REFERENCES test_steps(id) ON DELETE SET NULL;

-- Add indexes for AI tracking
CREATE INDEX IF NOT EXISTS idx_test_steps_ai_generated ON test_steps(is_ai_generated);
CREATE INDEX IF NOT EXISTS idx_test_steps_parent_step ON test_steps(parent_step_id);

-- ============================================
-- Add Adaptive Execution Fields to test_cases table
-- ============================================

ALTER TABLE test_cases
ADD COLUMN IF NOT EXISTS adaptive_decisions JSONB DEFAULT '{}' NOT NULL,
ADD COLUMN IF NOT EXISTS recovery_attempts INTEGER DEFAULT 0 NOT NULL,
ADD COLUMN IF NOT EXISTS execution_variance JSONB DEFAULT '{}' NOT NULL;

-- Add index for recovery tracking
CREATE INDEX IF NOT EXISTS idx_test_cases_recovery_attempts ON test_cases(recovery_attempts);

-- ============================================
-- Migrate Existing Data
-- ============================================

-- Migrate existing test definitions to have goals
-- Concatenate existing test steps into a natural language goal
UPDATE test_definitions
SET
    test_goal = 'Test: ' || name || '. Steps: ' || (
        SELECT string_agg(description, '; ' ORDER BY step_number)
        FROM test_steps
        WHERE test_steps.test_definition_id = test_definitions.id
        LIMIT 10  -- Limit to prevent extremely long goals
    ),
    plan_generation_status = 'approved',  -- Mark existing tests as having approved plans
    ai_generated_plan = jsonb_build_object(
        'plan_id', gen_random_uuid()::text,
        'steps', jsonb_agg(
            jsonb_build_object(
                'step_number', step_number,
                'description', description,
                'type', type,
                'verification', COALESCE(expected_result, 'Manual verification'),
                'confidence', 0.8,
                'fallback_strategies', '["retry_on_failure"]'::jsonb
            )
        ) ORDER BY step_number
    ),
    plan_metadata = jsonb_build_object(
        'migration_date', NOW()::text,
        'migrated_from', 'manual_steps',
        'legacy_test', true
    )
WHERE test_goal IS NULL;

-- Mark existing test steps as non-AI-generated
UPDATE test_steps
SET is_ai_generated = FALSE
WHERE is_ai_generated IS NULL OR is_ai_generated = TRUE;

-- ============================================
-- Add Comments for Documentation
-- ============================================

COMMENT ON COLUMN test_definitions.test_goal IS 'User''s natural language test goal/requirement for AI planning';
COMMENT ON COLUMN test_definitions.test_context IS 'Additional context for AI test planning';
COMMENT ON COLUMN test_definitions.plan_generation_status IS 'Status of AI plan generation: pending/generated/approved';
COMMENT ON COLUMN test_definitions.ai_generated_plan IS 'AI-generated test plan stored as JSON';
COMMENT ON COLUMN test_definitions.plan_metadata IS 'Metadata about plan generation process';

COMMENT ON COLUMN test_steps.is_ai_generated IS 'Flag indicating if step was AI-generated vs manually created';
COMMENT ON COLUMN test_steps.confidence_score IS 'AI confidence score for the step (0.0-1.0)';
COMMENT ON COLUMN test_steps.parent_step_id IS 'Self-referencing foreign key for step hierarchy';

COMMENT ON COLUMN test_cases.adaptive_decisions IS 'AI decisions made during test execution';
COMMENT ON COLUMN test_cases.recovery_attempts IS 'Number of recovery attempts during execution';
COMMENT ON COLUMN test_cases.execution_variance IS 'Deviations from the original test plan';

-- ============================================
-- Commit Transaction
-- ============================================

COMMIT;

-- ============================================
-- Verification Queries (run separately)
-- ============================================

-- Verify new columns were added
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'test_definitions'
-- AND column_name IN ('test_goal', 'test_context', 'plan_generation_status', 'ai_generated_plan', 'plan_metadata')
-- ORDER BY ordinal_position;

-- Verify data migration
-- SELECT id, name, test_goal, plan_generation_status
-- FROM test_definitions
-- LIMIT 5;

-- Verify AI tracking on test_steps
-- SELECT id, test_definition_id, description, is_ai_generated, confidence_score
-- FROM test_steps
-- LIMIT 5;