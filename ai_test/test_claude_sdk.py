#!/usr/bin/env python3
"""
Test script for Claude Agent SDK

This script tests the basic functionality of Claude Agent SDK
to verify if it can work with the current configuration.
"""

import asyncio
import sys
import os

async def test_basic_query():
    """Test basic query without tools"""
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions

        print("🧪 Testing Claude Agent SDK (basic query)...")
        print(f"API Key: {os.getenv('ANTHROPIC_API_KEY', 'NOT_SET')[:20]}...")
        print(f"Base URL: {os.getenv('ANTHROPIC_BASE_URL', 'NOT_SET')}")
        print(f"Model: {os.getenv('ANTHROPIC_MODEL', 'NOT_SET')}")

        async for message in query(
            prompt="Say 'Hello, Claude Agent SDK is working!' in exactly those words.",
            options=ClaudeAgentOptions(
                permission_mode="auto",
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
            ),
        ):
            print(f"📨 Message: {message}")
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(f"✅ Response: {block.text[:200]}")
                        return True
            break  # Only get first response

        return False

    except Exception as e:
        print(f"❌ Basic query failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_query_with_tools():
    """Test query with tools (Read, Write, Bash)"""
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions

        print("\n🧪 Testing Claude Agent SDK (with tools)...")

        async for message in query(
            prompt="List the files in the current directory using the Bash tool.",
            options=ClaudeAgentOptions(
                allowed_tools=["Bash"],
                permission_mode="auto",
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                load_timeout_ms=120000  # 2 minutes
            ),
        ):
            print(f"📨 Message: {message}")
            if hasattr(message, 'content'):
                for block in message.content:
                    if hasattr(block, 'text'):
                        print(f"✅ Response: {block.text[:300]}")
                        return True
            break  # Only get first response

        return False

    except Exception as e:
        print(f"❌ Query with tools failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Claude Agent SDK Test Suite")
    print("=" * 60)

    # Test 1: Basic query
    basic_success = await test_basic_query()

    # Test 2: Query with tools
    tools_success = await test_query_with_tools()

    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Basic Query: {'✅ PASS' if basic_success else '❌ FAIL'}")
    print(f"  Query with Tools: {'✅ PASS' if tools_success else '❌ FAIL'}")
    print("=" * 60)

    if basic_success or tools_success:
        print("✅ Claude Agent SDK is working!")
        return 0
    else:
        print("❌ Claude Agent SDK tests failed.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
