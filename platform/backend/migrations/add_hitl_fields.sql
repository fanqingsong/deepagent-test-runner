-- Migration Script: Add Human-in-the-Loop Fields
-- Version: 002
-- Date: 2026-05-19
-- Description: Add conversation tables and HITL fields for test planning dialog,
--              failure recovery, and regression test management.

BEGIN;

-- ============================================
-- Create conversation_threads table
-- ============================================

CREATE TABLE IF NOT EXISTS conversation_threads (
    id SERIAL PRIMARY KEY,
    test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE SET NULL,
    thread_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    metadata JSONB DEFAULT '{}' NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_threads_test_def
    ON conversation_threads(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_type
    ON conversation_threads(thread_type);
CREATE INDEX IF NOT EXISTS idx_conversation_threads_status
    ON conversation_threads(status);

-- ============================================
-- Create conversation_messages table
-- ============================================

CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}' NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_thread
    ON conversation_messages(thread_id);

-- ============================================
-- Add regression fields to test_definitions
-- ============================================

ALTER TABLE test_definitions
ADD COLUMN IF NOT EXISTS is_regression BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN IF NOT EXISTS regression_source_run_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_test_definitions_regression
    ON test_definitions(is_regression) WHERE is_regression = TRUE;

-- ============================================
-- Add HITL fields to test_runs
-- ============================================

ALTER TABLE test_runs
ADD COLUMN IF NOT EXISTS approved_by INTEGER,
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS failure_notified BOOLEAN DEFAULT FALSE NOT NULL;

-- ============================================
-- Comments
-- ============================================

COMMENT ON TABLE conversation_threads IS 'Multi-turn conversations between users and AI for test planning and failure recovery';
COMMENT ON TABLE conversation_messages IS 'Individual messages within a conversation thread';
COMMENT ON COLUMN test_definitions.is_regression IS 'Marks this test as a saved regression test from a successful run';
COMMENT ON COLUMN test_definitions.regression_source_run_id IS 'The run_id this regression test was saved from';
COMMENT ON COLUMN test_runs.approved_by IS 'User ID who approved this test run for execution';
COMMENT ON COLUMN test_runs.approved_at IS 'Timestamp when the test run was approved for execution';
COMMENT ON COLUMN test_runs.failure_notified IS 'Whether the failure notification conversation was created';

COMMIT;
