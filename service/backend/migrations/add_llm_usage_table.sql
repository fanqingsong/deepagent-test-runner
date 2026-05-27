-- LLM Usage tracking table
-- Stores per-call token usage for all LLM-powered agents

CREATE TABLE IF NOT EXISTS llm_usage (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    prompt_tokens BIGINT NOT NULL DEFAULT 0,
    completion_tokens BIGINT NOT NULL DEFAULT 0,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    duration_ms BIGINT NOT NULL DEFAULT 0,
    user_id INTEGER,
    test_run_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_llm_usage_created_at ON llm_usage (created_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_agent_type_created_at ON llm_usage (agent_type, created_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_user_id_created_at ON llm_usage (user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_llm_usage_test_run_id ON llm_usage (test_run_id);
