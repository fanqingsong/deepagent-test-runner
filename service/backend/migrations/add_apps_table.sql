-- Migration: Add apps table and is_draft/source_app_id to test_definitions

CREATE TABLE IF NOT EXISTS apps (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  url VARCHAR(500),
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  test_goal TEXT,
  test_context JSONB DEFAULT '{}',
  current_plan JSONB DEFAULT '{}',
  conversation_thread_id INTEGER REFERENCES conversation_threads(id) ON DELETE SET NULL,
  test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE SET NULL,
  latest_run_id VARCHAR(100),
  latest_result JSONB DEFAULT '{}',
  iteration_count INTEGER DEFAULT 0,
  icon VARCHAR(50) NOT NULL DEFAULT 'test-tube',
  color VARCHAR(20) NOT NULL DEFAULT '#0f62fe',
  created_by INTEGER REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apps_status ON apps(status);
CREATE INDEX IF NOT EXISTS idx_apps_created_by ON apps(created_by);

-- Add is_draft and source_app_id columns to test_definitions
ALTER TABLE test_definitions ADD COLUMN IF NOT EXISTS is_draft BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE test_definitions ADD COLUMN IF NOT EXISTS source_app_id INTEGER REFERENCES apps(id);
