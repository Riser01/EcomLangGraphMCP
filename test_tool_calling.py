#!/usr/bin/env python3
"""
Test script to verify tool calling functionality
"""
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.unified_chatbot_service import UnifiedChatbotService

async def test_tool_calling():
    """Test the tool calling functionality"""
    print("🧪 Testing Tool Calling Functionality")
    print("="*50)
    
    # Initialize the service
    try:
        service = UnifiedChatbotService()
        print("✅ Service initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize service: {e}")
        return
    
    # Check MCP status
    status = service.get_mcp_status()
    print(f"📊 MCP Status: {status}")
    
    # Test queries that should trigger tool calls
    test_queries = [
        "Hi, can you tell me about membership",  # Should use search_wiki
        "Can I get the status of my order ORDZW011?",  # Should use read_order_status
        "How do I list my restaurant on GreatBuy",  # Should use search_wiki
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n🔍 Test {i}: {query}")
        print("-" * 40)
        
        try:
            result = service.chat(user_input=query, session_id="test_session")
            
            print(f"💬 Response: {result['response'][:100]}...")
            print(f"🛠️  Tools used: {result['tools_used']}")
            print(f"📝 Steps: {len(result['intermediate_steps'])}")
            
            if result['tools_used'] > 0:
                print("✅ Tools were called!")
                for step in result['intermediate_steps']:
                    print(f"   - {step}")
            else:
                print("❌ No tools were called")
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
    
    # Cleanup
    try:
        await service.cleanup()
        print("\n🧹 Cleanup completed")
    except Exception as e:
        print(f"⚠️  Cleanup warning: {e}")

if __name__ == "__main__":
    asyncio.run(test_tool_calling())
