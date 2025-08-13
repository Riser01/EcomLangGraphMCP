import os
import re
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger

from .state import ChatState


class ChatbotService:
    """
    Service class that handles the core chatbot logic using OpenAI API.
    """
    
    def __init__(self):
        """Initialize the chatbot service with OpenAI client."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        
        # Get model from environment variable or use default
        model_name = os.getenv("MODEL", "gpt-3.5-turbo")
        
        # Initialize the OpenAI chat model
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.7,
            api_key=self.api_key,
            streaming=True  # Enable streaming for better user experience
        )
        
        # MCP tools will be set later
        self.mcp_tools = []
        
        # Define the system prompt template
        self.prompt_template = ChatPromptTemplate.from_messages([
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
        Process a user message and generate a response.
        
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
            formatted_prompt = self.prompt_template.format_messages(
                user_input=state["user_input"],
                context=context,
                turn_count=state.get("turn_count", 0)
            )
            
            # Generate response using OpenAI
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
    
    async def stream_response(self, state: ChatState):
        """
        Stream response for real-time chat experience.
        
        Args:
            state: Current conversation state
            
        Yields:
            Streamed response chunks
        """
        try:
            context = self._build_context(state.get("messages", []))
            
            formatted_prompt = self.prompt_template.format_messages(
                user_input=state["user_input"],
                context=context,
                turn_count=state.get("turn_count", 0)
            )
            
            # Stream the response
            async for chunk in self.llm.astream(formatted_prompt):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield "I apologize, but I encountered an error while processing your message."
