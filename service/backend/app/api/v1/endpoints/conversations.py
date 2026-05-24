"""
Conversation API Endpoints

REST API for human-in-the-loop test planning conversations and failure recovery.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.permissions import RequirePermission
from app.core.security import get_current_user
from app.models import ConversationThread, ConversationMessage, TestDefinition
from app.models.user import User
from app.models.test_case import TestCase
from app.models.test_run import TestRun
from app.schemas.conversation import (
    ApproveRequest,
    ConversationCreate,
    ConversationMessageResponse,
    ConversationResponse,
    FailureConversationResponse,
    FailureRecoveryRequest,
    SendMessageRequest,
    SendMessageResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversation thread linked to a test definition."""
    thread = ConversationThread(
        test_definition_id=request.test_definition_id,
        thread_type=request.thread_type,
        metadata_=request.metadata,
    )
    db.add(thread)
    await db.commit()
    await db.refresh(thread)
    return ConversationResponse(
        id=thread.id,
        test_definition_id=thread.test_definition_id,
        thread_type=thread.thread_type,
        status=thread.status,
        metadata=thread.metadata_,
        created_at=thread.created_at,
        messages=[],
    )


@router.get("/{thread_id}", response_model=ConversationResponse)
async def get_conversation(
    thread_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation thread with all its messages."""
    result = await db.execute(
        select(ConversationThread)
        .options(selectinload(ConversationThread.messages))
        .where(ConversationThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Conversation thread {thread_id} not found")

    return ConversationResponse(
        id=thread.id,
        test_definition_id=thread.test_definition_id,
        thread_type=thread.thread_type,
        status=thread.status,
        metadata=thread.metadata_,
        created_at=thread.created_at,
        messages=[
            ConversationMessageResponse(
                id=m.id,
                thread_id=m.thread_id,
                role=m.role,
                content=m.content,
                metadata=m.metadata_,
                created_at=m.created_at,
            )
            for m in thread.messages
        ],
    )


@router.post("/{thread_id}/messages", response_model=SendMessageResponse)
async def send_message(
    thread_id: int,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a user message and get an AI response with a refined plan."""
    result = await db.execute(
        select(ConversationThread)
        .options(selectinload(ConversationThread.messages))
        .where(ConversationThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
    if thread.status != "active":
        raise HTTPException(status_code=400, detail=f"Thread is {thread.status}, not active")

    user_msg = ConversationMessage(
        thread_id=thread_id,
        role="user",
        content=request.content,
    )
    db.add(user_msg)
    await db.flush()

    test_def = None
    if thread.test_definition_id:
        td_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == thread.test_definition_id)
        )
        test_def = td_result.scalar_one_or_none()

    history = [{"role": m.role, "content": m.content} for m in thread.messages]
    history.append({"role": "user", "content": request.content})

    updated_plan = None
    try:
        from app.agents.planner_agent import generate_test_plan, refine_test_plan

        goal = test_def.test_goal if test_def else ""
        url = test_def.url if test_def else ""
        current_plan = test_def.ai_generated_plan if test_def and test_def.ai_generated_plan else {}
        context = test_def.environment if test_def else {}

        # First message (no existing plan): generate from scratch.
        # Subsequent messages: refine the existing plan.
        if not current_plan or not current_plan.get("steps"):
            updated_plan = await generate_test_plan(
                goal=goal,
                url=url,
                context=context,
            )
        else:
            updated_plan = await refine_test_plan(
                goal=goal,
                url=url,
                current_plan=current_plan,
                conversation_history=history,
                user_feedback=request.content,
                context=context,
            )
    except Exception as e:
        logger.warning("Plan refinement failed for thread %d: %s", thread_id, e)
        updated_plan = test_def.ai_generated_plan if test_def else {}

    plan_text = ""
    if updated_plan and updated_plan.get("steps"):
        steps_text = "\n".join(
            f"  Step {s.get('step_number', i+1)}: {s.get('description', '')}"
            for i, s in enumerate(updated_plan["steps"])
        )
        plan_text = f"\n\nUpdated plan:\n{steps_text}"

    assistant_content = f"I've refined the test plan based on your feedback.{plan_text}"

    assistant_msg = ConversationMessage(
        thread_id=thread_id,
        role="assistant",
        content=assistant_content,
        metadata_={"plan": updated_plan} if updated_plan else {},
    )
    db.add(assistant_msg)

    if test_def and updated_plan:
        test_def.ai_generated_plan = updated_plan
        test_def.plan_generation_status = "generated"

    await db.commit()
    await db.flush()

    return SendMessageResponse(
        assistant_message=ConversationMessageResponse(
            id=assistant_msg.id,
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
            metadata=assistant_msg.metadata_,
            created_at=assistant_msg.created_at,
        ),
        updated_plan=updated_plan,
    )


@router.put("/{thread_id}/approve")
async def approve_conversation(
    thread_id: int,
    request: ApproveRequest,
    current_user: User = Depends(RequirePermission("update:test")),
    db: AsyncSession = Depends(get_db),
):
    """Approve the current plan in the conversation."""
    result = await db.execute(
        select(ConversationThread).where(ConversationThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    if thread.test_definition_id:
        td_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == thread.test_definition_id)
        )
        test_def = td_result.scalar_one_or_none()
        if test_def and request.modifications:
            plan = dict(test_def.ai_generated_plan or {})
            steps = list(plan.get("steps", []))
            for mod in request.modifications:
                for step in steps:
                    if step.get("step_number") == mod.step_number:
                        if mod.description:
                            step["description"] = mod.description
                        if mod.type:
                            step["type"] = mod.type
                        if mod.verification:
                            step["verification"] = mod.verification
                        break
            plan["steps"] = steps
            test_def.ai_generated_plan = plan

        if test_def:
            test_def.plan_generation_status = "approved"

    thread.status = "approved"
    await db.commit()

    return {
        "thread_id": thread_id,
        "status": "approved",
        "modifications_applied": len(request.modifications),
    }


@router.post("/{thread_id}/regenerate", response_model=SendMessageResponse)
async def regenerate_plan(
    thread_id: int,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fully regenerate the test plan with user feedback."""
    result = await db.execute(
        select(ConversationThread).where(ConversationThread.id == thread_id)
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")

    user_msg = ConversationMessage(
        thread_id=thread_id,
        role="user",
        content=request.content,
    )
    db.add(user_msg)
    await db.flush()

    test_def = None
    if thread.test_definition_id:
        td_result = await db.execute(
            select(TestDefinition).where(TestDefinition.id == thread.test_definition_id)
        )
        test_def = td_result.scalar_one_or_none()

    new_plan = None
    try:
        from app.agents.planner_agent import generate_test_plan

        goal = test_def.test_goal if test_def else ""
        url = test_def.url if test_def else ""
        context = test_def.environment if test_def else {}

        new_plan = await generate_test_plan(goal=goal, url=url, context=context)
    except Exception as e:
        logger.warning("Plan regeneration failed for thread %d: %s", thread_id, e)
        raise HTTPException(status_code=500, detail=f"Plan regeneration failed: {e}")

    steps_text = "\n".join(
        f"  Step {s.get('step_number', i+1)}: {s.get('description', '')}"
        for i, s in enumerate(new_plan.get("steps", []))
    )
    assistant_content = f"Here's the regenerated plan:\n{steps_text}"

    assistant_msg = ConversationMessage(
        thread_id=thread_id,
        role="assistant",
        content=assistant_content,
        metadata_={"plan": new_plan},
    )
    db.add(assistant_msg)

    if test_def and new_plan:
        test_def.ai_generated_plan = new_plan
        test_def.plan_generation_status = "generated"

    await db.commit()
    await db.flush()

    return SendMessageResponse(
        assistant_message=ConversationMessageResponse(
            id=assistant_msg.id,
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
            metadata=assistant_msg.metadata_,
            created_at=assistant_msg.created_at,
        ),
        updated_plan=new_plan,
    )


@router.get("/failure/{run_id}", response_model=FailureConversationResponse)
async def get_failure_conversation(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the failure recovery conversation for a specific run."""
    result = await db.execute(
        select(ConversationThread)
        .options(selectinload(ConversationThread.messages))
        .where(
            ConversationThread.thread_type == "failure_recovery",
            ConversationThread.metadata_["run_id"].as_string() == run_id,
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail=f"No failure conversation found for run {run_id}")

    run_result = await db.execute(
        select(TestRun).where(TestRun.run_id == run_id)
    )
    test_run = run_result.scalar_one_or_none()

    failed_steps = []
    if test_run:
        tc_result = await db.execute(
            select(TestCase).where(
                TestCase.run_id == test_run.id,
                TestCase.status.in_(["failed", "error"]),
            )
        )
        for tc in tc_result.scalars().all():
            failed_steps.append({
                "description": tc.description,
                "status": tc.status,
                "error": tc.error_message,
                "screenshot": tc.screenshot_path,
            })

    thread_resp = ConversationResponse(
        id=thread.id,
        test_definition_id=thread.test_definition_id,
        thread_type=thread.thread_type,
        status=thread.status,
        metadata=thread.metadata_,
        created_at=thread.created_at,
        messages=[
            ConversationMessageResponse(
                id=m.id,
                thread_id=m.thread_id,
                role=m.role,
                content=m.content,
                metadata=m.metadata_,
                created_at=m.created_at,
            )
            for m in thread.messages
        ],
    )

    return FailureConversationResponse(thread=thread_resp, failed_steps=failed_steps)


@router.post("/failure/{run_id}/respond")
async def respond_to_failure(
    run_id: str,
    request: FailureRecoveryRequest,
    current_user: User = Depends(RequirePermission("update:test")),
    db: AsyncSession = Depends(get_db),
):
    """Respond to a test failure with a recovery action."""
    result = await db.execute(
        select(ConversationThread)
        .where(
            ConversationThread.thread_type == "failure_recovery",
            ConversationThread.metadata_["run_id"].as_string() == run_id,
        )
    )
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(status_code=404, detail=f"No failure conversation for run {run_id}")

    user_msg = ConversationMessage(
        thread_id=thread.id,
        role="user",
        content=f"Recovery action: {request.action}. {json.dumps(request.params)}",
        metadata_={"action": request.action, "params": request.params},
    )
    db.add(user_msg)

    if request.action == "retry":
        from app.tasks.test_execution import retry_test_with_modifications
        run_result = await db.execute(
            select(TestRun).where(TestRun.run_id == run_id)
        )
        test_run = run_result.scalar_one_or_none()
        if test_run and test_run.test_definition_id:
            modified_plan = request.params.get("modified_plan")
            environment = request.params.get("environment", {})
            retry_test_with_modifications.delay(
                test_definition_id=test_run.test_definition_id,
                original_run_id=run_id,
                modified_plan=modified_plan,
                environment=environment,
            )
            assistant_content = "Retry initiated. A new test run is starting with the modified parameters."
        else:
            assistant_content = "Could not retry: test run or definition not found."
    elif request.action == "regenerate_step":
        assistant_content = "Please describe how you'd like the failed step to be modified, and I'll regenerate it."
    else:
        assistant_content = f"Recovery action '{request.action}' recorded. How would you like to proceed?"

    assistant_msg = ConversationMessage(
        thread_id=thread.id,
        role="assistant",
        content=assistant_content,
    )
    db.add(assistant_msg)
    await db.commit()

    return {"status": "ok", "action": request.action}
