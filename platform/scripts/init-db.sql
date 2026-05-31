-- Claude Code Tests Database Schema
-- This file is automatically run on PostgreSQL container initialization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Users table for authentication
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  email VARCHAR(255) UNIQUE NOT NULL,
  hashed_password VARCHAR(255) NOT NULL,
  is_active BOOLEAN DEFAULT true,
  is_admin BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Test definitions table
CREATE TABLE IF NOT EXISTS test_definitions (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  test_id VARCHAR(100) UNIQUE NOT NULL,
  url VARCHAR(500),
  environment JSONB DEFAULT '{}',
  tags TEXT[] DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by VARCHAR(100) DEFAULT 'system',
  version INTEGER DEFAULT 1,
  is_active BOOLEAN DEFAULT true
);

-- Test steps table
CREATE TABLE IF NOT EXISTS test_steps (
  id SERIAL PRIMARY KEY,
  test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE CASCADE,
  step_number INTEGER NOT NULL,
  description TEXT NOT NULL,
  type VARCHAR(50) NOT NULL,
  params JSONB NOT NULL,
  expected_result TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test versions table
CREATE TABLE IF NOT EXISTS test_versions (
  id SERIAL PRIMARY KEY,
  test_definition_id INTEGER REFERENCES test_definitions(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  snapshot JSONB NOT NULL,
  change_description TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by VARCHAR(100) DEFAULT 'system'
);

-- Test runs table
CREATE TABLE IF NOT EXISTS test_runs (
  id SERIAL PRIMARY KEY,
  run_id VARCHAR(100) UNIQUE NOT NULL,
  test_definition_id INTEGER REFERENCES test_definitions(id),
  start_time BIGINT NOT NULL,
  end_time BIGINT,
  total_tests INTEGER DEFAULT 0,
  passed INTEGER DEFAULT 0,
  failed INTEGER DEFAULT 0,
  skipped INTEGER DEFAULT 0,
  total_duration INTEGER DEFAULT 0,
  status VARCHAR(50) DEFAULT 'pending',
  environment VARCHAR(100),
  triggered_by VARCHAR(100),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test cases table
CREATE TABLE IF NOT EXISTS test_cases (
  id SERIAL PRIMARY KEY,
  run_id INTEGER REFERENCES test_runs(id) ON DELETE CASCADE,
  test_definition_id INTEGER REFERENCES test_definitions(id),
  test_id VARCHAR(100) NOT NULL,
  description TEXT,
  status VARCHAR(50) NOT NULL,
  duration INTEGER NOT NULL,
  start_time BIGINT NOT NULL,
  end_time BIGINT NOT NULL,
  error_message TEXT,
  screenshot_path TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Test step results table
CREATE TABLE IF NOT EXISTS test_step_results (
  id SERIAL PRIMARY KEY,
  test_case_id INTEGER REFERENCES test_cases(id) ON DELETE CASCADE,
  step_number INTEGER NOT NULL,
  description TEXT NOT NULL,
  status VARCHAR(50) NOT NULL,
  error_message TEXT,
  screenshot_path TEXT,
  duration INTEGER,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  test_definition_ids INTEGER[] NOT NULL,
  cron_expression VARCHAR(100) NOT NULL,
  environment VARCHAR(100) DEFAULT 'development',
  is_active BOOLEAN DEFAULT true,
  next_run_time TIMESTAMP WITH TIME ZONE,
  last_run_time TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by VARCHAR(100) DEFAULT 'system'
);

-- Webhooks table
CREATE TABLE IF NOT EXISTS webhooks (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  url VARCHAR(500) NOT NULL,
  secret VARCHAR(255),
  test_definition_ids INTEGER[],
  events TEXT[] NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_test_definitions_test_id ON test_definitions(test_id);
CREATE INDEX IF NOT EXISTS idx_test_definitions_tags ON test_definitions USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_test_runs_status ON test_runs(status);
CREATE INDEX IF NOT EXISTS idx_test_runs_start_time ON test_runs(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_test_cases_run_id ON test_cases(run_id);
CREATE INDEX IF NOT EXISTS idx_test_cases_test_definition ON test_cases(test_definition_id);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run_time) WHERE is_active = true;

-- Insert sample data
-- Default admin user (password: admin123 - CHANGE THIS IN PRODUCTION!)
INSERT INTO users (username, email, hashed_password, is_admin) VALUES
('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpLaEmc0i', true)
ON CONFLICT (username) DO NOTHING;

-- Sample test definition
INSERT INTO test_definitions (name, test_id, description, url) VALUES
('Sample Login Test', 'sample-login-test', 'A sample test for login functionality', 'https://example.com/login')
ON CONFLICT (test_id) DO NOTHING;
