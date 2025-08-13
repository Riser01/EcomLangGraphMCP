#!/usr/bin/env python3
"""
Test script for the ConversationGraph to verify MCP integration works correctly.
"""

import asyncio
import sys
import os
from loguru import logger

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set some basic environment variables for testing
os.environ.setdefault("OPENAI_API_KEY", "test-key")  # Will be overridden if real key exists
os.environ.setdefault("MODEL", "gpt-3.5-turbo")


async def test_conversation_graph():
    """Test the ConversationGraph initialization and MCP integration."""
    logger.info("🧪 Starting ConversationGraph test...")
    
    try:
        from src.conversation_graph import ConversationGraph
        
        # Create ConversationGraph instance
        logger.info("🔄 Creating ConversationGraph instance...")
        graph = ConversationGraph()
        
        # Check MCP status
        mcp_status = graph.get_mcp_status()
        logger.info(f"📊 MCP Status: {mcp_status}")
        
        # Check available tools
        tool_names = graph.get_available_tools()
        logger.info(f"📋 Available tools: {tool_names}")
        
        # Test chat with a simple greeting (should not require tools)
        test_session_id = "test-session-001"
        test_input = "Hello, how are you?"
        
        logger.info(f"💬 Testing chat with input: '{test_input}'")
        response = graph.chat(test_input, test_session_id)
        
        logger.info(f"🤖 Chat response: {response}")
        
        # Clean up
        await graph.cleanup()
        
        logger.success("🎉 ConversationGraph test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ ConversationGraph test failed: {str(e)}")
        logger.exception("Full error details:")
        return False


async def main():
    """Main test function."""
    logger.info("🚀 Starting ConversationGraph integration test...")
    
    success = await test_conversation_graph()
    
    if success:
        logger.success("✅ All tests passed!")
        return 0
    else:
        logger.error("❌ Tests failed!")
        return 1


if __name__ == "__main__":
    # Run the test
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
