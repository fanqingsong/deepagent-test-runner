"""
Content Builder Subagent — Specialized for researching topics and writing content.

Provides web research via Tavily and LLM-powered content generation
for blog posts and social media.
"""

from deepagents import CompiledSubAgent
from langchain.agents import create_agent

from app.agents.chat_assistant.content_builder_tools import (
    research_topic,
    write_blog_post,
    write_social_post,
)


def create_content_builder_graph(llm):
    """Create the compiled graph for the content builder subagent."""
    return create_agent(
        model=llm,
        tools=[research_topic, write_blog_post, write_social_post],
        system_prompt=(
            "You are a content writing specialist. You research topics and produce "
            "high-quality written content for blogs and social media.\n\n"
            "**Your tools:**\n"
            "1. research_topic(query, max_results) — search the web for information\n"
            "2. write_blog_post(topic, research_notes, tone, target_audience) — write a blog post\n"
            "3. write_social_post(topic, research_notes, platform, tone) — write a social post\n\n"
            "**Workflow (REQUIRED):**\n"
            "1. ALWAYS call research_topic FIRST with a specific query\n"
            "2. For deeper coverage, make 2-3 research calls with different query angles\n"
            "3. Pass the combined research notes to write_blog_post or write_social_post\n"
            "4. Present the final content to the user\n\n"
            "**Rules:**\n"
            "- NEVER write content without researching first\n"
            "- NEVER delegate to other agents or subagents\n"
            "- NEVER try to save files or access the filesystem\n"
            "- Always include the research findings in your content\n"
            "- Respond in the same language as the user's message\n\n"
            "**Content quality:**\n"
            "- Blog posts: structured with headers, actionable insights, clear CTA\n"
            "- LinkedIn: professional tone, hook first, 3-5 hashtags\n"
            "- Twitter: concise threads, one idea per tweet, engaging hook\n"
        ),
    )


def get_content_builder_subagent(llm):
    """Get the compiled content builder subagent."""
    return CompiledSubAgent(
        name="content-builder",
        description=(
            "Research topics and write content — blog posts, social media posts, articles. "
            "Use this when the user asks to write a blog post, LinkedIn post, tweet/thread, "
            "article, or any long-form or social content. The agent researches the topic first, "
            "then generates structured content."
        ),
        runnable=create_content_builder_graph(llm),
    )
