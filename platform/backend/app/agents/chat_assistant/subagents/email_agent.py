"""
Email Subagent — Specialized for sending emails and querying history.

Enforces a confirmation flow: preview first, then send after user approval.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.email_tools import preview_email, send_email_tool, query_sent_emails


def create_email_graph(llm):
    """Create the compiled graph for the email subagent."""
    return create_agent(
        model=llm,
        tools=[preview_email, send_email_tool, query_sent_emails],
        system_prompt=(
            "You are an email specialist. You help users send emails and check sent email history.\n\n"
            "**IMPORTANT — Confirmation Flow:**\n"
            "When the user asks to send an email:\n"
            "1. First call preview_email to generate a preview\n"
            "2. Show the preview to the user and ask for confirmation\n"
            "3. ONLY call send_email_tool after the user explicitly confirms (e.g. '确认', '发送吧', 'yes', 'send')\n"
            "4. If the user says no or wants changes, update the content and preview again\n\n"
            "When the user asks about sent emails, use query_sent_emails.\n"
            "Always respond in the same language as the user's message."
        ),
    )


def get_email_subagent(llm):
    """Get the compiled email subagent."""
    return CompiledSubAgent(
        name="email",
        description=(
            "Send emails and query sent email history. "
            "Use this when the user wants to send an email, compose a message, "
            "or check previously sent emails."
        ),
        runnable=create_email_graph(llm),
    )
