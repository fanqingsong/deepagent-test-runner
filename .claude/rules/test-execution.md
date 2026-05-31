# Test Execution Flow

## Pipeline

1. **Schedule Trigger**: Temporal Schedule detects due cron → triggers `ScheduleExecutionWorkflow`
2. **Job Creation**: Creates TestRun record with status='pending'
3. **Test Execution**: Workflow calls execution with test_definition_id
4. **LangGraph Pipeline**: `supervisor_graph.py` routes to planner/executor/reviewer nodes
5. **Browser Automation**: `executor_agent.py` uses `create_react_agent` with Playwright tools
6. **Result Saving**: `ExecutionService.save_test_results()` saves:
   - Summary to `test_runs` table
   - Individual step results to `test_cases` table
7. **Dashboard Update**: Frontend queries PostgreSQL for latest results

## LangGraph Supervisor Graph

```mermaid
flowchart TD
    START((START)) --> route_from_start{{route_from_start}}

    route_from_start -->|"mode=full_pipeline & goal"| planner_node
    route_from_start -->|"mode=execute_only"| executor_node

    planner_node[Planner Node<br/>generate_test_plan] --> route_after_planner{{route_after_planner}}
    route_after_planner -->|"plan_error"| error_handler_node
    route_after_planner -->|"success"| executor_node

    executor_node[Executor Node<br/>interpret_and_execute_batch] --> route_after_executor{{route_after_executor}}
    route_after_executor -->|"execution_error"| error_handler_node
    route_after_executor -->|"mode=plan_and_execute"| result_builder_node
    route_after_executor -->|"success"| reviewer_node

    reviewer_node[Reviewer Node<br/>review_test_results] --> result_builder_node

    error_handler_node[Error Handler Node<br/>retry or finalize] --> route_after_error{{route_after_error}}
    route_after_error -->|"retry_count ≤ max<br/>& failed_phase set"| executor_node
    route_after_error -->|"retry exhausted"| result_builder_node

    result_builder_node[Result Builder Node<br/>build final_result] --> END((END))

    executor_node -.->|"create_react_agent<br/>+ Playwright Tools"| Browser[Browser]
```

## Test Execution Verification

1. Check test_runs table for summary records
2. Check test_cases table for step-by-step results
3. Verify status transitions: pending → running → passed/failed
4. Confirm timestamps and durations are saved correctly
