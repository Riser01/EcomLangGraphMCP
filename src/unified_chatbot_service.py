import uuid
import os
import warnings
import asyncio
import nest_asyncio
from typing import Dict, Any, List, Union, Optional
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger

from .state import ChatState

# Apply nest_asyncio to allow running async code from sync contexts
nest_asyncio.apply()


class UnifiedChatbotService:
    """
    Unified chatbot service that combines simple OpenAI chat with advanced
    LangGraph ReAct agent capabilities and MCP tool integration.

    This class provides both basic chat functionality and advanced tool-based
    conversation management in a single interface.
    """

    def __init__(self):
        """Initialize the unified chatbot service."""
        # Memory for conversation state
        self.memory = MemorySaver()

        # Initialize LLM with fallback support
        self.llm = self._initialize_llm()

        # MCP integration
        self._mcp_client = None
        self.mcp_tools = []
        self._initialized = False

        # Default MCP configuration
        self.mcp_config = {
            "GreatBuy-support": {
                "command": "python",
                "args": ["./mcp_server_remote.py"],
                "transport": "stdio"
            }
        }

        # System prompt template for simple chat mode
        self.simple_prompt_template = ChatPromptTemplate.from_messages([
            ("system", """<ROLE>
You are a smart agent with an ability to use tools.
You will be given a question and you will use the tools to answer the question.
Pick the most relevant tool to answer the question.
If you are failed to answer the question, try different tools to get context.
Your answer should be very polite and professional.
</ROLE>
----
<INSTRUCTIONS>
Step 1: Analyze the question
- Analyze user's question and final goal.
- If the user's question is consist of multiple sub-questions, split them into smaller sub-questions.

Step 2: Pick the most relevant tool
- Pick the most relevant tool to answer the question.
- If you are failed to answer the question, try different tools to get context.

Step 3: Answer the question
- Answer the question in the same language as the question.
- Your answer should be very polite and professional.

Step 4: Provide the source of the answer(if applicable)
- If you've used the tool, provide the source of the answer.
- Valid sources are either a website(URL) or a document(PDF, etc).

Guidelines:
- If you've used the tool, your answer should be based on the tool's output(tool's output is more important than your own knowledge).
- If you've used the tool, and the source is valid URL, provide the source(URL) of the answer.
- Skip providing the source if the source is not URL.
- Answer in the same language as the question.
- Answer should be concise and to the point.
- Avoid response your output with any other information than the answer and the source.
</INSTRUCTIONS>
----
<OUTPUT_FORMAT>
(concise answer to the question)


</OUTPUT_FORMAT>

            Current conversation turn: {turn_count}
            Context: {context}
            Tool Results: {tool_results}"""),
            ("human", "{user_input}")
        ])

        # System message for ReAct agent mode
        self.react_system_message = """You are a helpful GreatBuy customer support agent. You have access to tools that can help you answer customer questions about orders, membership, and GreatBuy services.

IMPORTANT: Always use the appropriate tool when the customer asks about:
- Order status (use read_order_status tool with order ID)
- Order cancellation (use update_order_status tool with order ID and 'cancelled' status)
- GreatBuy services, membership, policies, fees (use search_wiki tool)

After using a tool, analyze its output and provide a direct, helpful answer to the user. Do not ask the user for information you can find with a tool.

For simple greetings or general conversation, you can respond directly without using tools.

Be polite, professional, and helpful in all your responses."""

        # Initialize MCP tools and ReAct agent
        try:
            logger.info("Starting unified chatbot initialization...")
            asyncio.run(self._async_initialize_mcp_tools())
        except Exception as e:
            logger.error(f"❌ Critical error during MCP initialization: {e}")

        # Create the ReAct agent
        self.agent = self._create_react_agent()

    def _initialize_llm(self) -> Union[ChatOpenAI, ChatGoogleGenerativeAI]:
        """Initialize the LLM with preference for OpenAI, fallback to Google Gemini."""
        openai_api_key = os.getenv("OPENAI_API_KEY")
        google_api_key = os.getenv("GOOGLE_API_KEY")
        provider_preference = os.getenv("PROVIDER_PREFERENCE", "openai").lower()

        # Prefer OpenAI if available and preference is set to openai
        if provider_preference == "openai" and openai_api_key:
            try:
                model_name = os.getenv("MODEL", "gpt-4o")
                logger.info(f"Using OpenAI: {model_name}")
                return ChatOpenAI(
                    model=model_name,
                    temperature=0.7,
                    api_key=openai_api_key,
                    streaming=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI: {str(e)}")

        # Fallback to Google Gemini
        if google_api_key:
            try:
                model_name = os.getenv("FALLBACK_MODEL", "gemini-1.5-flash")
                logger.info(f"Using Google Gemini: {model_name}")
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=0.7,
                    google_api_key=google_api_key,
                    streaming=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize Google Gemini: {str(e)}")

        # Try OpenAI as last resort if Google Gemini failed
        if openai_api_key:
            try:
                model_name = os.getenv("MODEL", "gpt-4o")
                logger.info(f"Using OpenAI as fallback: {model_name}")
                return ChatOpenAI(
                    model=model_name,
                    temperature=0.7,
                    api_key=openai_api_key,
                    streaming=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI as fallback: {str(e)}")

        # If neither works, raise an error
        raise ValueError(
            "No valid API key found. Please set either OPENAI_API_KEY or GOOGLE_API_KEY environment variable."
        )

    async def _async_initialize_mcp_tools(self):
        """Asynchronously starts the MCP client and loads the tools."""
        try:
            logger.info("🔄 Starting MCP client initialization...")

            try:
                from langchain_mcp_adapters.client import MultiServerMCPClient
                logger.info("✅ MCP libraries imported successfully")

                self._mcp_client = MultiServerMCPClient(self.mcp_config)
                logger.info("✅ MCP client created successfully")
                logger.info(f"🔧 MCP Config: {self.mcp_config}")

                self.mcp_tools = await self._mcp_client.get_tools()
                logger.info("✅ MCP tools retrieved successfully")

                if self.mcp_tools:
                    logger.success(f"✅ Successfully loaded {len(self.mcp_tools)} MCP tools")
                    for i, tool in enumerate(self.mcp_tools, 1):
                        logger.info(f"   {i}. {tool.name} - {getattr(tool, 'description', 'No description')}")
                else:
                    logger.warning("⚠️  MCP tools loaded but list is empty")

                self._initialized = True

            except ImportError as e:
                logger.warning(f"❌ MCP libraries not available: {str(e)}")
                logger.info("📋 Required packages: langchain-mcp-adapters")
                self.mcp_tools = []

        except Exception as e:
            logger.error(f"❌ Critical error in MCP client initialization: {str(e)}")
            logger.exception("Full error details:")
            self.mcp_tools = []
            await self._cleanup_mcp()

        # Final status report
        if self.mcp_tools:
            logger.success(f"🎉 MCP Client initialized with {len(self.mcp_tools)} tools")
        else:
            logger.warning("⚠️  MCP Client initialized with NO tools - running in fallback mode")

    def _create_react_agent(self):
        """Create a ReAct agent with MCP tools."""
        tool_count = len(self.mcp_tools)
        logger.info(f"🤖 Creating ReAct agent with {tool_count} tools")

        if self.mcp_tools:
            tool_names = [getattr(tool, 'name', 'Unknown') for tool in self.mcp_tools]
            logger.info(f"🛠️  Agent will use tools: {tool_names}")
        else:
            logger.warning("⚠️  Agent will be created WITHOUT tools (basic responses only)")

        try:
            agent = create_react_agent(
                model=self.llm,
                tools=self.mcp_tools,
                checkpointer=self.memory,
                state_modifier=self.react_system_message
            )

            logger.success(f"✅ ReAct agent created successfully with {tool_count} tools")
            return agent

        except Exception as e:
            logger.error(f"❌ Failed to create ReAct agent: {str(e)}")
            logger.exception("Full error details:")
            raise

    async def _cleanup_mcp(self):
        """Cleanup MCP client resources."""
        if self._mcp_client:
            try:
                await self._mcp_client.close()
                logger.info("✅ MCP client closed successfully")
            except Exception as e:
                logger.error(f"❌ Error closing MCP client: {str(e)}")

    async def cleanup(self):
        """Gracefully shuts down the MCP client and its subprocesses."""
        await self._cleanup_mcp()

    # ========== SIMPLE CHAT MODE METHODS (from ChatbotService) ==========

    def set_mcp_tools(self, tools: List):
        """
        Set the MCP tools for this service.

        Args:
            tools: List of MCP tools
        """
        self.mcp_tools = tools
        logger.info(f"Set {len(tools)} MCP tools for chatbot service")

    def process_message(self, state: ChatState) -> Dict[str, Any]:
        """
        Process a user message using simple chat mode (without ReAct agent).

        Args:
            state: Current conversation state

        Returns:
            Updated state with bot response
        """
        try:
            logger.info(f"Processing message for session {state.get('session_id', 'unknown')}")

            # Prepare the context from recent messages
            context = self._build_context(state.get("messages", []))

            # Format the prompt
            formatted_prompt = self.simple_prompt_template.format_messages(
                user_input=state["user_input"],
                context=context,
                turn_count=state.get("turn_count", 0),
                tool_results=""  # No tools in simple mode
            )

            # Generate response using LLM
            response = self.llm.invoke(formatted_prompt)

            logger.success("Successfully generated response")

            return {
                "bot_response": response.content,
                "context": context,
                "error": "",
                "turn_count": state.get("turn_count", 0) + 1,
                "messages": [
                    HumanMessage(content=state["user_input"]),
                    AIMessage(content=response.content)
                ]
            }

        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            logger.error(error_msg)
            return {
                "bot_response": "I apologize, but I encountered an error while processing your message. Please try again.",
                "error": error_msg,
                "turn_count": state.get("turn_count", 0),
                "messages": [
                    HumanMessage(content=state["user_input"]),
                    AIMessage(content="I apologize, but I encountered an error while processing your message. Please try again.")
                ]
            }

    async def stream_response(self, state: ChatState):
        """
        Stream response for real-time chat experience (simple mode).

        Args:
            state: Current conversation state

        Yields:
            Streamed response chunks
        """
        try:
            context = self._build_context(state.get("messages", []))

            formatted_prompt = self.simple_prompt_template.format_messages(
                user_input=state["user_input"],
                context=context,
                turn_count=state.get("turn_count", 0),
                tool_results=""
            )

            # Stream the response
            async for chunk in self.llm.astream(formatted_prompt):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield "I apologize, but I encountered an error while processing your message."

    def _build_context(self, messages: list) -> str:
        """
        Build context string from recent conversation messages.

        Args:
            messages: List of conversation messages

        Returns:
            Context string summarizing recent conversation
        """
        if not messages:
            return "Starting a new conversation."

        # Get last few messages for context (max 5 exchanges)
        recent_messages = messages[-10:] if len(messages) > 10 else messages

        context_parts = []
        for msg in recent_messages:
            if hasattr(msg, 'content'):
                msg_type = "User" if isinstance(msg, HumanMessage) else "Assistant"
                # Truncate very long messages
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                context_parts.append(f"{msg_type}: {content}")

        return " | ".join(context_parts) if context_parts else "New conversation."

    # ========== REACT AGENT MODE METHODS (from ConversationGraph) ==========

    def chat(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """
        Process user input through the ReAct agent (advanced mode with tools).

        Args:
            user_input: The user's message
            session_id: Session identifier for conversation continuity

        Returns:
            Dictionary containing response and metadata
        """
        try:
            logger.info(f"💬 Processing message through ReAct agent: {user_input[:50]}...")
            tool_count = len(self.mcp_tools)
            logger.info(f"🛠️  Agent has {tool_count} tools available")

            # Fallback to direct LLM if no tools are available or agent not initialized
            if tool_count == 0 or not self.agent:
                logger.warning("⚠️  No tools available or agent not initialized, using direct LLM response")
                try:
                    response = self.llm.invoke([HumanMessage(content=user_input)])
                    return {
                        "response": response.content,
                        "intermediate_steps": ["Direct LLM response (no tools available)"],
                        "error": "",
                        "tools_used": 0
                    }
                except Exception as e:
                    logger.error(f"❌ Direct LLM response failed: {str(e)}")
                    return {
                        "response": "I apologize, but I'm having technical difficulties. Please try again later.",
                        "intermediate_steps": [f"❌ Error: {str(e)}"],
                        "error": str(e),
                        "tools_used": 0
                    }

            config = {"configurable": {"thread_id": session_id}}
            input_data = {"messages": [HumanMessage(content=user_input)]}

            logger.info("🤖 ReAct Agent: Starting to process query...")
            
            # Try async invoke first, fallback to sync
            try:
                # Use async invoke if available
                result = asyncio.run(self.agent.ainvoke(input_data, config))
            except Exception as async_error:
                logger.warning(f"⚠️ Async invoke failed: {str(async_error)}, trying sync invoke")
                try:
                    result = self.agent.invoke(input_data, config)
                except Exception as sync_error:
                    logger.error(f"❌ Both async and sync invoke failed. Async: {async_error}, Sync: {sync_error}")
                    return {
                        "response": "I apologize, but I'm having trouble processing your request. Please try again.",
                        "intermediate_steps": [f"❌ Agent invoke error: {str(sync_error)}"],
                        "error": str(sync_error),
                        "tools_used": 0
                    }

            # --- RESPONSE AND STEP PARSING ---
            messages = result.get("messages", [])
            final_response = ""
            intermediate_steps = []
            tools_used_count = 0

            if messages and isinstance(messages[-1], AIMessage):
                final_response = messages[-1].content
                logger.info("💬 ReAct Agent: Final response captured")

            # Collect all tool usage and result steps from the conversation history
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        tools_used_count += 1
                        tool_name = tool_call.get('name', 'Unknown')
                        tool_args = tool_call.get('args', {})
                        log_msg = f"🛠️ Agent decided to use tool: {tool_name} with args {tool_args}"
                        if log_msg not in intermediate_steps:
                            intermediate_steps.append(log_msg)
                        logger.info(f"🛠️ ReAct Agent: Found tool call for {tool_name}")
                
                # Capture the actual output from the tool
                elif isinstance(msg, ToolMessage):
                    log_msg = f"✅ Tool '{getattr(msg, 'name', msg.tool_call_id)}' returned: {msg.content}"
                    if log_msg not in intermediate_steps:
                        intermediate_steps.append(log_msg)
                    logger.info(log_msg)

            if not final_response and not any(isinstance(m, AIMessage) and m.tool_calls for m in messages):
                final_response = "I was unable to find a specific tool for your request. Could you please clarify?"
                logger.warning("⚠️ Agent did not use a tool and did not provide a clear final answer.")
            elif not final_response:
                final_response = "I've processed your request, but I'm having trouble formulating a final response. Please check the steps to see the result."
                logger.warning("⚠️ No final response captured from agent, using fallback message.")

            logger.success(f"✅ ReAct agent completed processing (Tools used: {tools_used_count})")

            return {
                "response": final_response,
                "intermediate_steps": intermediate_steps,
                "error": "",
                "tools_used": tools_used_count
            }

        except Exception as e:
            error_msg = f"Error in ReAct agent processing: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full error trace:")

            fallback_response = "I apologize, but I encountered an error while processing your request. Please try again."

            return {
                "response": fallback_response,
                "intermediate_steps": [f"❌ Error: {error_msg}"],
                "error": error_msg,
                "tools_used": 0
            }

    # ========== UTILITY METHODS ==========

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        tool_names = []
        for tool in self.mcp_tools:
            tool_name = getattr(tool, 'name', 'Unknown')
            tool_names.append(tool_name)

        logger.info(f"📋 Available tool names: {tool_names}")
        return tool_names

    def get_mcp_status(self) -> Dict[str, Any]:
        """Get detailed MCP connection status and tool information."""
        try:
            mcp_available = self.is_mcp_available()
            tool_count = len(self.mcp_tools)
            tool_names = self.get_available_tools()

            status = {
                "mcp_available": mcp_available,
                "tool_count": tool_count,
                "tool_names": tool_names,
                "mcp_client_tools": len(self.mcp_tools) if self._mcp_client else 0,
                "connection_status": "Connected" if mcp_available else "Disconnected"
            }

            logger.info(f"📊 MCP Status: {status}")
            return status

        except Exception as e:
            logger.error(f"❌ Error getting MCP status: {str(e)}")
            return {
                "mcp_available": False,
                "tool_count": 0,
                "tool_names": [],
                "mcp_client_tools": 0,
                "connection_status": "Error",
                "error": str(e)
            }

    def is_mcp_available(self) -> bool:
        """Check if MCP tools are available."""
        available = bool(self.mcp_tools and self._initialized)
        logger.debug(f"🔍 MCP availability check: {available} (tools: {len(self.mcp_tools)}, initialized: {self._initialized})")
        return available

    def get_tool_by_name(self, tool_name: str) -> Optional[object]:
        """Get a specific tool by name."""
        for tool in self.mcp_tools:
            if tool.name == tool_name:
                logger.info(f"🔍 Found tool: {tool_name}")
                return tool
        return None

    def describe_tools(self) -> str:
        """Get a description of all available tools."""
        if not self.mcp_tools:
            return "No MCP tools available"

        descriptions = []
        for tool in self.mcp_tools:
            descriptions.append(f"- {tool.name}: {getattr(tool, 'description', 'No description available')}")

        return "Available MCP Tools:\n" + "\n".join(descriptions)

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        try:
            config = {"configurable": {"thread_id": session_id}}
            state = self.agent.get_state(config)

            messages = []
            for msg in state.values.get("messages", []):
                if isinstance(msg, HumanMessage):
                    messages.append({"type": "human", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    messages.append({"type": "ai", "content": msg.content})

            return messages

        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []

    def get_current_provider(self) -> Dict[str, str]:
        """Get information about the current LLM provider being used."""
        try:
            if isinstance(self.llm, ChatOpenAI):
                return {"provider": "OpenAI", "model": self.llm.model_name}
            elif isinstance(self.llm, ChatGoogleGenerativeAI):
                return {"provider": "Google", "model": self.llm.model}
            else:
                 # Fallback for other potential models
                if hasattr(self.llm, 'model_name'):
                    return {"provider": "Unknown", "model": self.llm.model_name}
                if hasattr(self.llm, 'model'):
                    return {"provider": "Unknown", "model": self.llm.model}
                return {"provider": "Unknown", "model": "Unknown"}
        except Exception as e:
            logger.error(f"Error getting provider info: {str(e)}")
            return {"provider": "Error", "model": "Error"}