from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
import httpx
from typing import Any, Dict, AsyncIterable

memory = MemorySaver()


@tool
def frameworx_question(
    question: str = "What are the Open-APIs required to integrate partners into a Wholesale Broadband platform?",
):
    """Use this to answer questions relating to TM Forum.

    Args:
        question: The question to answer (e.g., "What are the Open-APIs required to integrate partners into a Wholesale Broadband platform?").

    Returns:
        A string containing the answer, or an error message if the request fails.
    """
    try:
        # Replace with actual API call to get the answer
        response = {"answer": "This is a dummy response."}
        return response
    except httpx.HTTPError as e:
        return {"error": f"API request failed: {e}"}
    except ValueError:
        return {"error": "Invalid JSON response from API."}


class AIVAAgent:
    def __init__(self):
        self.model = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
        self.tools = [frameworx_question]
        self.graph = create_react_agent(
            self.model, tools=self.tools, checkpointer=memory
        )

    def invoke(self, query, sessionId) -> str:
        print("--------------------------------")
        print(f"Invoking agent for query: {query}, session_id: {sessionId}")
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        print("--------------------------------")
        print(f"Streaming response for query: {query}, session_id: {sessionId}")
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": sessionId}}

        for item in self.graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                isinstance(message, AIMessage)
                and message.tool_calls
                and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up the answer from TM Forum...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing the answer from TM Forum..",
                }
        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        current_state = self.graph.get_state(config)
        messages = current_state.values["messages"]

        last_message = messages[-1]

        # from the last message check if there is a ToolMessage before we hit a HumanMessage
        # if there is ToolMessage, we assume the tool is invoked and we have final response
        # if not we assume the tool needs additional inputs from user
        for i in range(len(messages) - 2, 0, -1):
            current = messages[i]
            if isinstance(current, ToolMessage):
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": last_message.content,
                }
            elif isinstance(current, HumanMessage):
                break

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": last_message.content,
        }

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
